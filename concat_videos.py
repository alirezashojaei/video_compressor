import ffmpeg 
import argparse
import os
import sys

def probe_video(input_path):
    """
    Probes a video file to get its properties, such as resolution and frame rate.

    Args:
        input_path (str): The path to the video file.

    Returns:
        dict: A dictionary containing the video's properties.
    """
    try:
        probe = ffmpeg.probe(input_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream is None:
            raise ValueError(f"No video stream found in {input_path}")

        return {
            'width': int(video_stream['width']),
            'height': int(video_stream['height']),
            'r_frame_rate': video_stream.get('r_frame_rate', '0/1')
        }
    except ffmpeg.Error as e:
        sys.stderr.write(f"Error probing {input_path}: {e.stderr.decode('utf8')}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"An unexpected error occurred while probing {input_path}: {e}\n")
        return None

def concat_videos_ffmpeg_python(input_videos, output_path, preset="ultrafast", video_codec="libx264", threads=0):
    """
    Concatenates multiple video files into a single file using ffmpeg-python.

    Args:
        input_videos (list): A list of paths to the input video files.
        output_path (str): The path to save the concatenated video file.
        preset (str): The FFmpeg encoding speed preset.
        video_codec (str): The video codec to use for the output.
        threads (int): The number of threads for encoding.
    """
    if not input_videos:
        print("No input videos provided.", file=sys.stderr)
        return

    # Probe all videos to determine the most common resolution and frame rate
    video_properties = [probe_video(v) for v in input_videos]
    video_properties = [p for p in video_properties if p]  # Filter out any videos that failed to probe

    if not video_properties:
        print("Could not retrieve properties from any input videos.", file=sys.stderr)
        return

    # Determine the target resolution and frame rate (e.g., from the first video)
    target_width = video_properties[0]['width']
    target_height = video_properties[0]['height']
    target_fps_str = video_properties[0]['r_frame_rate']
    
    # Prepare the input streams for concatenation
    input_streams = []
    for video_path in input_videos:
        stream = ffmpeg.input(video_path)
        # Ensure all videos have the same resolution and pixel format
        processed_video = stream.video.filter('scale', width=target_width, height=target_height).filter('setsar', 1).filter('format', 'yuv420p')
        processed_audio = stream.audio.filter('aformat', sample_fmts='fltp', sample_rates='44100', channel_layouts='stereo')
        input_streams.append(processed_video)
        input_streams.append(processed_audio)

    # Concatenate the video and audio streams
    concatenated = ffmpeg.concat(*input_streams, v=1, a=1).node

    video_stream = concatenated[0]
    audio_stream = concatenated[1]
    
    # Define the output operation with encoding parameters
    output_params = {
        'c:v': video_codec,
        'preset': preset,
        'threads': threads,
        'movflags': '+faststart',
        'c:a': 'aac',
        'b:a': '192k'  # A reasonable default audio bitrate
    }

    output_operation = ffmpeg.output(video_stream, audio_stream, output_path, **output_params)

    print("FFmpeg command parameters derived:")
    print(f"  Target Resolution: {target_width}x{target_height}")
    print(f"  Target FPS: {target_fps_str}")
    print(f"  Preset: {preset}, Codec: {video_codec}, Threads: {threads}")

    try:
        # Execute the FFmpeg command
        output_operation.run(overwrite_output=True, quiet=False)
        print(f"Videos successfully concatenated and saved to {output_path}")

    except ffmpeg.Error as e:
        error_msg = e.stderr.decode('utf8') if e.stderr else 'Unknown FFmpeg error'
        print(f"An FFmpeg error occurred: {error_msg}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        raise

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description='Concatenate multiple video files using FFmpeg.')
    
    parser.add_argument('input_files', nargs='+', help='Paths to the input video files.')
    parser.add_argument('-o', '--output', required=True, help='Output file path.')
    
    # Advanced options
    parser.add_argument('--preset', default='ultrafast', 
                      choices=['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow'],
                      help='Encoding speed/compression ratio (default: ultrafast).')
    parser.add_argument('--codec', default='libx264', 
                      choices=['libx264', 'libx265', 'copy'],
                      help='Video codec (default: libx264). "copy" can be used for stream copying if all inputs are identical.')
    parser.add_argument('--threads', type=int, default=0,
                      help='Number of threads to use (0 = auto-detect, default: 0)')
    parser.add_argument('--overwrite', action='store_true', 
                      help='Overwrite output file if it exists.')
    
    return parser.parse_args()

def main():
    """The main function to execute the script."""
    args = parse_arguments()
    
    for f in args.input_files:
        if not os.path.isfile(f):
            print(f"Error: Input file '{f}' not found.", file=sys.stderr)
            sys.exit(1)
    
    if os.path.exists(args.output) and not args.overwrite:
        response = input(f"Warning: Output file '{args.output}' already exists. Overwrite? (y/N): ").strip().lower()
        if response != 'y':
            print("Operation cancelled by user.")
            sys.exit(0)

    print("\nStarting video concatenation...")
    print(f"Input videos: {', '.join(args.input_files)}")
    print(f"Output will be saved to: {args.output}")
    
    try:
        concat_videos_ffmpeg_python(
            input_videos=args.input_files,
            output_path=args.output,
            preset=args.preset,
            video_codec=args.codec,
            threads=args.threads
        )
        print("\nConcatenation completed successfully.")
    except Exception as e:
        print(f"\nAn error occurred during concatenation. See details above.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
