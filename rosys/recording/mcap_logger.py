from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from mcap.writer import CompressionType, Writer

from .. import rosys

NANOSECONDS_PER_SECOND = 1_000_000_000

_COMPRESSION_MAP: dict[str, CompressionType] = {
    'zstd': CompressionType.ZSTD,
    'lz4': CompressionType.LZ4,
    'none': CompressionType.NONE,
}


class McapLogger:
    """Records sensor data to MCAP files for replay and analysis in Foxglove Studio.

    Supports automatic file rotation by size and disk budget enforcement.
    """

    def __init__(
        self,
        *,
        output_dir: Path | str = '~/.rosys/mcap',
        max_file_size_mb: float = 100,
        max_total_size_mb: float = 1000,
        compression: str = 'zstd',
        chunk_size: int = 1_048_576,
        auto_start: bool = True,
    ) -> None:
        self.log = logging.getLogger('rosys.mcap_logger')
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = int(max_file_size_mb * 1_048_576)
        self.max_total_size = int(max_total_size_mb * 1_048_576)
        self.compression = _COMPRESSION_MAP.get(compression, CompressionType.ZSTD)
        self.chunk_size = chunk_size

        self._writer: Writer | None = None
        self._file: BinaryIO | None = None
        self._file_path: Path | None = None
        self._topics: dict[str, int] = {}
        self._schemas: dict[str, tuple[str, dict]] = {}
        self._message_count: int = 0
        self._approximate_file_size: int = 0
        self._file_counter: int = 0
        self._is_recording: bool = False
        self._warned_topics: set[str] = set()

        if auto_start:
            rosys.on_startup(self.start)
        rosys.on_shutdown(self.stop)

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def current_file_size(self) -> int:
        if self._file_path and self._file_path.exists():
            return self._file_path.stat().st_size
        return 0

    @property
    def total_size(self) -> int:
        return sum(f.stat().st_size for f in self.output_dir.glob('*.mcap'))

    @property
    def file_count(self) -> int:
        return len(list(self.output_dir.glob('*.mcap')))

    def add_topic(self, topic: str, *, schema_name: str, schema: dict) -> None:
        """Register a topic with a JSON schema.

        Can be called before or after start(). If called while recording,
        the topic is immediately available for logging.
        """
        self._schemas[topic] = (schema_name, schema)
        if self._writer is not None:
            self._register_topic(topic, schema_name, schema)

    def start(self) -> None:
        if self._is_recording:
            return
        self._open_new_file()
        self._is_recording = True
        self.log.info('started MCAP recording: %s', self._file_path)

    def stop(self) -> None:
        if not self._is_recording:
            return
        self._is_recording = False
        self._close_file()
        self.log.info('stopped MCAP recording (%d messages total)', self._message_count)

    def log_message(self, topic: str, data: dict, *, timestamp_ns: int | None = None) -> None:
        if not self._is_recording or self._writer is None:
            return
        if topic not in self._topics:
            if topic not in self._warned_topics:
                self.log.warning('unknown topic: %s', topic)
                self._warned_topics.add(topic)
            return
        if timestamp_ns is None:
            timestamp_ns = int(rosys.time() * NANOSECONDS_PER_SECOND)
        encoded = json.dumps(data).encode()
        self._writer.add_message(
            channel_id=self._topics[topic],
            log_time=timestamp_ns,
            data=encoded,
            publish_time=timestamp_ns,
        )
        self._message_count += 1
        self._approximate_file_size += len(encoded)
        if self._approximate_file_size >= self.max_file_size:
            self._rotate()

    def _register_topic(self, topic: str, schema_name: str, schema_dict: dict) -> None:
        assert self._writer is not None
        schema_id = self._writer.register_schema(
            name=schema_name,
            encoding='jsonschema',
            data=json.dumps(schema_dict).encode(),
        )
        self._topics[topic] = self._writer.register_channel(
            schema_id=schema_id,
            topic=topic,
            message_encoding='json',
        )

    def _open_new_file(self) -> None:
        timestamp = datetime.now(tz=UTC).strftime('%Y%m%d_%H%M%S')
        self._file_path = self.output_dir / f'{timestamp}_{os.getpid()}_{self._file_counter:04d}.mcap'
        self._file_counter += 1
        self._file = open(self._file_path, 'wb')
        self._writer = Writer(self._file, compression=self.compression, chunk_size=self.chunk_size)
        self._writer.start(profile='rosys', library='rosys-mcap-logger')
        self._topics.clear()
        self._approximate_file_size = 0
        for topic, (schema_name, schema_dict) in self._schemas.items():
            self._register_topic(topic, schema_name, schema_dict)

    def _close_file(self) -> None:
        try:
            if self._writer is not None:
                self._writer.finish()
        finally:
            self._writer = None
            if self._file is not None:
                self._file.close()
                self._file = None
            self._topics.clear()

    def _rotate(self) -> None:
        self.log.info('rotating MCAP file (%.1f MB)', self.current_file_size / 1_048_576)
        self._close_file()
        self._enforce_disk_budget()
        self._open_new_file()

    def _enforce_disk_budget(self) -> None:
        file_stats = [(f, f.stat()) for f in self.output_dir.glob('*.mcap')]
        file_stats.sort(key=lambda fs: fs[1].st_mtime)
        total = sum(s.st_size for _, s in file_stats)
        while total > self.max_total_size and file_stats:
            oldest, stat = file_stats.pop(0)
            oldest.unlink()
            total -= stat.st_size
            self.log.info('deleted old recording: %s (freed %.1f MB)', oldest.name, stat.st_size / 1_048_576)

    def developer_ui(self) -> None:
        from nicegui import ui  # noqa: PLC0415

        with ui.column():
            ui.label('MCAP Recording').classes('text-center text-bold')
            with ui.grid(columns='auto auto').classes('gap-y-1'):
                ui.label('Recording:')
                recording_icon = ui.icon('stop')
                ui.label('Messages:')
                message_label = ui.label('0')
                ui.label('File:')
                file_label = ui.label('-')
                ui.label('File size:')
                size_label = ui.label('-')
                ui.label('Total:')
                total_label = ui.label('-')
                ui.label('Files:')
                files_label = ui.label('-')

            def update() -> None:
                recording_icon.name = 'fiber_manual_record' if self._is_recording else 'stop'
                recording_icon.classes(replace='text-red' if self._is_recording else 'text-grey')
                message_label.text = str(self._message_count)
                file_label.text = self._file_path.name if self._file_path else '-'
                size_label.text = f'{self.current_file_size / 1_048_576:.1f} MB'
                total_label.text = f'{self.total_size / 1_048_576:.1f} / {self.max_total_size / 1_048_576:.0f} MB'
                files_label.text = str(self.file_count)

            ui.timer(2.0, update)

            with ui.row():
                ui.button('Start', on_click=self.start) \
                    .bind_enabled_from(self, '_is_recording', backward=lambda x: not x)
                ui.button('Stop', on_click=self.stop) \
                    .bind_enabled_from(self, '_is_recording')
