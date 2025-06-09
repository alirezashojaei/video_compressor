# Video Compressor

Python scripts for video compression and concatenation using FFmpeg.

## Features

- Video compression with reduction levels (1-10)
- Video concatenation with automatic format matching
- Multi-threaded encoding
- Safe file handling

## Installation

1. Install Python 3.6+
2. Install required package:
   ```bash
   pip install ffmpeg-python
   ```
3. Install FFmpeg:
   - macOS: `brew install ffmpeg`
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - Windows: Download from [FFmpeg's website](https://ffmpeg.org/download.html)

## Usage

### Video Compression

```bash
python video_compressor.py input.mp4 -r REDUCTION_LEVEL [options]
```

Basic examples:
```bash
# Medium compression
python video_compressor.py input.mp4 -r 5

# Maximum compression
python video_compressor.py input.mp4 -r 10 -o small_output.mp4

# Best quality
python video_compressor.py input.mp4 -r 1 -o high_quality.mp4
```

Options:
```
-r, --reduction-level {1-10}  Compression level (1=best quality, 10=smallest size)
-o, --output                  Output file path
--preset {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}
--codec {libx264,libx265}    Video codec
--threads THREADS            Number of threads (0=auto)
--overwrite                  Overwrite existing files
```

### Video Concatenation

```bash
python concat_videos.py video1.mp4 video2.mp4 video3.mp4 -o output.mp4
```

Options:
```
-o, --output         Output file path (required)
--preset {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}
--codec {libx264,libx265,copy}
--threads THREADS    Number of threads (0=auto)
--overwrite          Overwrite existing files
```

## License

This project is open source and available under the [MIT License](LICENSE).
