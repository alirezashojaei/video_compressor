import ffmpeg  # ffmpeg-python library
import argparse
import os
import sys


def get_fps_from_stream(stream_data):
    """Extract FPS from stream data, preferring r_frame_rate."""
    if not stream_data:
        return None
    
    fps_str = None
    if 'r_frame_rate' in stream_data and stream_data['r_frame_rate'] not in ('0/0', None, ''):
        fps_str = stream_data['r_frame_rate']
    elif 'avg_frame_rate' in stream_data and stream_data['avg_frame_rate'] not in ('0/0', None, ''):
        fps_str = stream_data['avg_frame_rate']

    if fps_str:
        try:
            num, den = map(float, fps_str.split('/'))
            if den == 0:
                return None
            return num / den
        except ValueError:
            return None
    return None

def probe_video(input_path):
    """Probe video file to get stream information, including FPS."""
    try:
        probe = ffmpeg.probe(input_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
        
        original_fps = None
        if video_stream:
            original_fps = get_fps_from_stream(video_stream)

        return {
            'has_video': video_stream is not None,
            'has_audio': audio_stream is not None,
            'width': int(video_stream['width']) if video_stream and 'width' in video_stream else None,
            'height': int(video_stream['height']) if video_stream and 'height' in video_stream else None,
            'fps': original_fps,
            'duration': float(probe['format']['duration']) if 'duration' in probe['format'] and probe['format']['duration'] is not None else None
        }
    except ffmpeg.Error as e:
        raise Exception(f"Error probing video: {e.stderr.decode('utf8') if e.stderr else 'Unknown error probing video'}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred during probing: {e}")


def reduce_video_size_ffmpeg_python(input_path, output_path, reduction_level,
                                   preset="ultrafast", video_codec="libx264", threads=0):
    """
    Reduces video size using ffmpeg-python based on a reduction level.

    Args:
        input_path (str): Path to the input video file.
        output_path (str): Path to save the compressed video file.
        reduction_level (int): An integer from 1 (min reduction) to 10 (max reduction).
        preset (str): FFmpeg encoding speed preset.
        video_codec (str): Video codec to use.
        threads (int): Number of threads for encoding.
    """
    try:
        video_info = probe_video(input_path)
        if not video_info['has_video']:
            raise ValueError("Input file does not contain a video stream")

        original_width = video_info['width']
        original_fps = video_info['fps']

        # --- Determine FFmpeg parameters based on reduction_level ---

        # 1. CRF (Constant Rate Factor)
        # Range: ~20 (better quality, larger size) to ~38 (lower quality, smaller size)
        # Level 1: CRF ~20-21, Level 10: CRF ~36-38
        target_crf = 20 + int(round((reduction_level - 1) * (38 - 20) / 9.0))
        target_crf = max(18, min(51, target_crf)) # Clamp to valid CRF range for H.264

        # 2. Resolution Scaling (maintaining aspect ratio)
        scale_width_param = None
        MIN_WIDTH = 240 # Minimum width to avoid overly small videos
        if original_width:
            scale_percentage = 1.0 # Default: no scaling for level 1-2
            if 3 <= reduction_level <= 4:
                scale_percentage = 0.80  # 80% of original width
            elif 5 <= reduction_level <= 6:
                scale_percentage = 0.65  # 65% (e.g. ~720p from 1080p)
            elif 7 <= reduction_level <= 8:
                scale_percentage = 0.50  # 50% (e.g. ~540p from 1080p)
            elif reduction_level >= 9:
                scale_percentage = 0.35  # 35% (e.g. ~360p-480p from 1080p)
            
            if scale_percentage < 1.0:
                candidate_width = int(original_width * scale_percentage)
                # Ensure width is even and not below MIN_WIDTH
                candidate_width = max(MIN_WIDTH, candidate_width - (candidate_width % 2))
                if candidate_width < original_width:
                    scale_width_param = candidate_width
        elif reduction_level >= 7: # Fallback if original width unknown and high reduction
            scale_width_param = 640 
        elif reduction_level >= 4:
             scale_width_param = 720


        # 3. Audio Bitrate
        if 1 <= reduction_level <= 2:
            target_audio_bitrate = "128k"
        elif 3 <= reduction_level <= 4:
            target_audio_bitrate = "96k"
        elif 5 <= reduction_level <= 7:
            target_audio_bitrate = "64k"
        else:  # 8-10
            target_audio_bitrate = "48k"

        # 4. FPS (Frames Per Second)
        target_fps_value = None # By default, don't change FPS
        apply_fps_filter = False
        if original_fps and reduction_level >= 9: # More aggressive FPS reduction for highest levels
            if original_fps > 30.1: # Account for fractional FPS like 59.94
                target_fps_value = 30
                apply_fps_filter = True
            elif original_fps > 25.1 and original_fps <= 30.1:
                target_fps_value = 24 # or 25
                apply_fps_filter = True
        
        # --- Prepare FFmpeg stream operations ---
        input_stream = ffmpeg.input(input_path)
        video_stream = input_stream.video
        
        # Apply scaling if determined
        if scale_width_param:
            video_stream = ffmpeg.filter(video_stream, 'scale', w=scale_width_param, h='-1')

        # Apply FPS filter if determined
        if apply_fps_filter and target_fps_value:
            video_stream = ffmpeg.filter(video_stream, 'fps', fps=target_fps_value, round='down')

        video_params = {
            'c:v': video_codec,
            'preset': preset,
            'crf': str(target_crf),
            'threads': threads,
            'movflags': '+faststart',
            'pix_fmt': 'yuv420p',
            'tune': 'zerolatency',
            'x264opts': 'no-scenecut',
            'refs': '1',
            'bf': '1',
            'deblock': '-1:-1'
        }
        
        # Add GOP settings if FPS is being explicitly set (can help with seeking)
        if apply_fps_filter and target_fps_value:
            video_params['g'] = str(int(target_fps_value * 2)) # GOP size
            video_params['keyint_min'] = str(int(target_fps_value))

        output_streams_args = [video_stream]
        
        if video_info['has_audio']:
            audio_stream = input_stream.audio
            audio_params = {'c:a': 'aac', 'b:a': target_audio_bitrate, 'ar': '44100'} # Standard sample rate
            output_streams_args.extend([audio_stream])
            all_params = {**video_params, **audio_params}
            output_operation = ffmpeg.output(*output_streams_args, output_path, **all_params)
        else:
            print("No audio stream found or processing video only.")
            output_operation = ffmpeg.output(video_stream, output_path, **video_params, an=None)
        
        print(f"FFmpeg command parameters derived:")
        print(f"  CRF: {target_crf}")
        if scale_width_param:
            print(f"  Target Width: {scale_width_param} (aspect ratio maintained)")
        else:
            print(f"  Target Width: Original")
        if apply_fps_filter and target_fps_value:
            print(f"  Target FPS: {target_fps_value}")
        else:
            print(f"  Target FPS: Original (or FFmpeg default)")
        if video_info['has_audio']:
            print(f"  Audio Bitrate: {target_audio_bitrate}")
        print(f"  Preset: {preset}, Codec: {video_codec}, Threads: {threads}")


        # Execute FFmpeg command
        ffmpeg.run(output_operation, overwrite_output=True, quiet=False)

        print(f"Video successfully compressed and saved to {output_path}")

    except ffmpeg.Error as e:
        error_msg = e.stderr.decode('utf8') if e.stderr else 'Unknown FFmpeg error'
        print(f"An FFmpeg error occurred: {error_msg}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        raise

def parse_arguments():
    parser = argparse.ArgumentParser(description='Reduce video file size using FFmpeg based on a reduction level.')
    
    parser.add_argument('input_file', help='Path to the input video file')
    parser.add_argument('-o', '--output', help='Output file path (default: <input>_compressed.<ext>)')
    
    parser.add_argument('-r', '--reduction-level', type=int, required=True, choices=range(1, 11),
                        help='Reduction level from 1 (min reduction, best quality) to 10 (max reduction, lowest quality)')
    
    # Advanced options (optional)
    parser.add_argument('--preset', default='ultrafast', 
                      choices=['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow'],
                      help='Encoding speed/compression ratio (default: ultrafast). Slower presets can offer better compression for the same CRF.')
    parser.add_argument('--codec', default='libx264', 
                      choices=['libx264', 'libx265'],
                      help='Video codec (default: libx264; libx265 is more efficient but might be slower and less compatible).')
    parser.add_argument('--threads', type=int, default=0,
                      help='Number of threads to use (0 = auto-detect, default: 0)')
    parser.add_argument('--overwrite', action='store_true', 
                      help='Overwrite output file if it exists')
    
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    if not args.output:
        name, ext = os.path.splitext(args.input_file)
        args.output = f"{name}_compressed{ext}"
    
    if not os.path.isfile(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.", file=sys.stderr)
        sys.exit(1)
    
    if os.path.exists(args.output) and not args.overwrite:
        response = input(f"Warning: Output file '{args.output}' already exists. Overwrite? (y/N): ").strip().lower()
        if response != 'y':
            print("Operation cancelled by user.")
            sys.exit(0)
        args.overwrite = True # Proceed with overwrite if user confirmed

    print(f"\nProcessing: {args.input_file}")
    print(f"Reduction Level: {args.reduction_level}")
    print(f"Output will be saved to: {args.output}")
    
    try:
        reduce_video_size_ffmpeg_python(
            input_path=args.input_file,
            output_path=args.output,
            reduction_level=args.reduction_level,
            preset=args.preset,
            video_codec=args.codec,
            threads=args.threads
        )
        print("\nCompression completed.")
    except Exception as e:
        # The reduce_video_size_ffmpeg_python function already prints detailed errors
        print(f"\nError during compression. See details above.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
