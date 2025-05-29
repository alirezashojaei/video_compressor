# Video Compressor

A Python script for reducing video file size using FFmpeg with intelligent compression presets. The script automatically adjusts multiple parameters to achieve the desired file size reduction while maintaining reasonable quality.

## Features

- Simple reduction level system (1-10) for easy compression
- Automatic resolution and quality adjustments based on reduction level
- Optimized for speed with minimal quality loss
- Maintains aspect ratio during resizing
- Automatic audio bitrate adjustment
- Smart frame rate handling
- Multi-threaded encoding for faster processing
- Safe file handling with overwrite protection

## Installation

1. Ensure you have Python 3.6+ installed
2. Install the required package:
   ```bash
   pip install ffmpeg-python
   ```
3. Make sure FFmpeg is installed on your system:
   - macOS: `brew install ffmpeg`
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - Windows: Download from [FFmpeg's official website](https://ffmpeg.org/download.html)

## Usage

```bash
python video_compressor.py input.mp4 -r REDUCTION_LEVEL [options]
```

### Basic Examples

1. **Basic compression** (level 5 - medium reduction):
   ```bash
   python video_compressor.py input.mp4 -r 5
   ```

2. **Maximum compression** (level 10 - smallest file size):
   ```bash
   python video_compressor.py input.mp4 -r 10 -o small_output.mp4
   ```

3. **Minimum compression** (level 1 - best quality):
   ```bash
   python video_compressor.py input.mp4 -r 1 -o high_quality.mp4
   ```

4. **Use H.265 for better compression** (slower but more efficient):
   ```bash
   python video_compressor.py input.mp4 -r 6 --codec libx265
   ```

### Reduction Levels

The script uses a simple scale from 1 to 10 to control compression:

| Level | Description | Resolution | CRF | Audio Bitrate | FPS |
|-------|-------------|------------|-----|---------------|-----|
| 1-2   | Minimal     | Original   | 20-22 | 128k        | Original |
| 3-4   | Light       | ~80%       | 24-26 | 96k         | Original |
| 5-6   | Medium      | ~65%       | 28-30 | 96k         | Original |
| 7-8   | High        | ~50%       | 32-34 | 64k         | Original |
| 9-10  | Maximum     | ~35%       | 36-38 | 48k         | 24-30 |

### Advanced Options

```
positional arguments:
  input_file           Path to the input video file

options:
  -h, --help            show this help message and exit
  -o, --output         Output file path (default: <input>_compressed.<ext>)
  -r, --reduction-level {1,2,3,4,5,6,7,8,9,10}
                        Reduction level from 1 (min reduction, best quality) to 10 (max reduction, lowest quality)
  --preset {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}
                        Encoding speed/compression ratio (default: ultrafast)
  --codec {libx264,libx265}
                        Video codec (default: libx264; libx265 is more efficient but might be slower and less compatible)
  --threads THREADS    Number of threads to use (0 = auto-detect, default: 0)
  --overwrite          Overwrite output file if it exists
```

### Tips

- Start with level 5 and adjust up or down based on your needs
- Levels 1-3 are best when quality is critical
- Levels 7-10 are good for reducing file size significantly when quality is less important
- The `ultrafast` preset is recommended for quick conversions
- For better compression efficiency, try the `fast` or `medium` presets (but encoding will be slower)

## License

This project is open source and available under the [MIT License](LICENSE).
