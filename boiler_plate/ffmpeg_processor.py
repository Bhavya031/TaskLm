#!/usr/bin/env python3
"""
Advanced Media Processor
A comprehensive tool for video/audio analysis, compression, conversion, and optimization
Leverages NVIDIA NVENC hardware acceleration when available
"""

import os
import sys
import json
import subprocess
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class ProcessingMode(Enum):
    COMPRESS = "compress"
    CONVERT = "convert"
    EXTRACT_AUDIO = "extract_audio"
    STREAMING_OPTIMIZE = "streaming_optimize"
    QUALITY_REDUCE = "quality_reduce"
    THUMBNAIL = "thumbnail"
    METADATA = "metadata"

@dataclass
class MediaInfo:
    """Container for media file information"""
    filepath: str
    duration: float
    size_mb: float
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    video_bitrate: Optional[int] = None
    audio_bitrate: Optional[int] = None
    resolution: Optional[Tuple[int, int]] = None
    fps: Optional[float] = None
    has_video: bool = False
    has_audio: bool = False
    format_name: str = ""

class MediaProcessor:
    """Advanced media processing with hardware acceleration support"""
    
    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self.supported_formats = {
            'video': ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv', '.m4v'],
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma']
        }
        self.setup_logging()
        self.check_ffmpeg()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('media_processor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def check_ffmpeg(self):
        """Verify FFmpeg and hardware acceleration availability"""
        try:
            # Check FFmpeg availability
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, check=True)
            self.logger.info("FFmpeg found and operational")
            
            # Check for NVIDIA encoders
            encoders_result = subprocess.run(['ffmpeg', '-encoders'], 
                                           capture_output=True, text=True, check=True)
            
            self.has_nvenc = 'h264_nvenc' in encoders_result.stdout
            self.has_av1_nvenc = 'av1_nvenc' in encoders_result.stdout
            self.has_hevc_nvenc = 'hevc_nvenc' in encoders_result.stdout
            
            if self.has_nvenc:
                self.logger.info("NVIDIA NVENC encoders detected")
            
        except subprocess.CalledProcessError:
            self.logger.error("FFmpeg not found or not working properly")
            sys.exit(1)
        except FileNotFoundError:
            self.logger.error("FFmpeg not installed or not in PATH")
            sys.exit(1)
    
    def analyze_media(self, filepath: str) -> MediaInfo:
        """Analyze media file and extract comprehensive information"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', filepath
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            # Extract basic info
            format_info = data.get('format', {})
            streams = data.get('streams', [])
            
            media_info = MediaInfo(
                filepath=filepath,
                duration=float(format_info.get('duration', 0)),
                size_mb=float(format_info.get('size', 0)) / (1024 * 1024),
                format_name=format_info.get('format_name', 'unknown')
            )
            
            # Analyze streams
            for stream in streams:
                codec_type = stream.get('codec_type')
                
                if codec_type == 'video':
                    media_info.has_video = True
                    media_info.video_codec = stream.get('codec_name')
                    media_info.video_bitrate = int(stream.get('bit_rate', 0)) if stream.get('bit_rate') else None
                    media_info.resolution = (
                        int(stream.get('width', 0)),
                        int(stream.get('height', 0))
                    )
                    
                    # Calculate FPS
                    fps_str = stream.get('r_frame_rate', '0/1')
                    if '/' in fps_str:
                        num, den = map(int, fps_str.split('/'))
                        media_info.fps = num / den if den != 0 else 0
                
                elif codec_type == 'audio':
                    media_info.has_audio = True
                    media_info.audio_codec = stream.get('codec_name')
                    media_info.audio_bitrate = int(stream.get('bit_rate', 0)) if stream.get('bit_rate') else None
            
            return media_info
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to analyze {filepath}: {e}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse ffprobe output: {e}")
            raise
    
    def print_media_info(self, media_info: MediaInfo):
        """Display comprehensive media information"""
        print("\n" + "="*60)
        print(f"📁 FILE: {os.path.basename(media_info.filepath)}")
        print("="*60)
        print(f"📊 Size: {media_info.size_mb:.2f} MB")
        print(f"⏱️  Duration: {self.format_duration(media_info.duration)}")
        print(f"📦 Format: {media_info.format_name}")
        
        if media_info.has_video:
            print(f"\n🎥 VIDEO:")
            print(f"   Codec: {media_info.video_codec}")
            if media_info.resolution:
                print(f"   Resolution: {media_info.resolution[0]}x{media_info.resolution[1]}")
            if media_info.fps:
                print(f"   FPS: {media_info.fps:.2f}")
            if media_info.video_bitrate:
                print(f"   Bitrate: {media_info.video_bitrate:,} bps")
        
        if media_info.has_audio:
            print(f"\n🔊 AUDIO:")
            print(f"   Codec: {media_info.audio_codec}")
            if media_info.audio_bitrate:
                print(f"   Bitrate: {media_info.audio_bitrate:,} bps")
        
        print("="*60)
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in human readable format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def get_processing_options(self, media_info: MediaInfo) -> Dict[str, str]:
        """Generate processing options based on media analysis"""
        options = {}
        
        if media_info.has_video:
            # Compression options
            if media_info.size_mb > 100:
                options['1'] = "🗜️  Compress video (reduce file size)"
            
            # Quality reduction
            options['2'] = "📉 Reduce quality (lower resolution/bitrate)"
            
            # Streaming optimization
            options['3'] = "🌐 Optimize for streaming (web-friendly)"
            
            # Format/Extension conversion
            options['4'] = "🔄 Convert format/extension (MP4, WebM, AVI, MKV, MOV)"
            
            # Audio extraction
            if media_info.has_audio:
                options['5'] = "🎵 Extract audio (MP3/AAC)"
            
            # Thumbnail generation
            options['6'] = "🖼️  Generate thumbnail"
        
        elif media_info.has_audio:
            # Audio compression
            if media_info.size_mb > 10:
                options['1'] = "🗜️  Compress audio (reduce file size)"
            
            # Format/Extension conversion
            options['2'] = "🔄 Convert format/extension (MP3, AAC, WAV, FLAC, OGG)"
            
            # Quality reduction
            options['3'] = "📉 Reduce audio quality"
        
        # Metadata operations
        options['7'] = "ℹ️  Show detailed metadata"
        options['0'] = "❌ Exit"
        
        return options
    
    def compress_video(self, media_info: MediaInfo, output_path: str, 
                      compression_level: str = "medium") -> bool:
        """Compress video with hardware acceleration when available"""
        
        # Determine encoder and settings
        if self.use_gpu and self.has_nvenc:
            if media_info.video_codec == 'h264':
                encoder = 'h264_nvenc'
            elif media_info.video_codec in ['hevc', 'h265']:
                encoder = 'hevc_nvenc' if self.has_hevc_nvenc else 'h264_nvenc'
            else:
                encoder = 'h264_nvenc'
        else:
            encoder = 'libx264'
        
        # Compression presets
        presets = {
            'light': {'crf': '23', 'preset': 'fast'},
            'medium': {'crf': '28', 'preset': 'medium'},
            'heavy': {'crf': '32', 'preset': 'slow'}
        }
        
        settings = presets.get(compression_level, presets['medium'])
        
        cmd = ['ffmpeg', '-i', media_info.filepath, '-c:v', encoder]
        
        if encoder.startswith('h264_nvenc') or encoder.startswith('hevc_nvenc'):
            cmd.extend(['-preset', 'fast', '-cq', settings['crf']])
        else:
            cmd.extend(['-crf', settings['crf'], '-preset', settings['preset']])
        
        # Audio settings
        if media_info.has_audio:
            cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
        
        cmd.extend(['-y', output_path])
        
        return self.run_ffmpeg_command(cmd, "Compressing video")
    
    def get_format_options(self, media_info: MediaInfo) -> Dict[str, Dict[str, str]]:
        """Get available format conversion options"""
        if media_info.has_video:
            return {
                'mp4': {'container': 'mp4', 'video_codec': 'h264_nvenc' if (self.use_gpu and self.has_nvenc) else 'libx264', 'audio_codec': 'aac'},
                'webm': {'container': 'webm', 'video_codec': 'libvpx-vp9', 'audio_codec': 'libopus'},
                'avi': {'container': 'avi', 'video_codec': 'libx264', 'audio_codec': 'aac'},
                'mkv': {'container': 'mkv', 'video_codec': 'h264_nvenc' if (self.use_gpu and self.has_nvenc) else 'libx264', 'audio_codec': 'aac'},
                'mov': {'container': 'mov', 'video_codec': 'libx264', 'audio_codec': 'aac'},
            }
        else:
            return {
                'mp3': {'container': 'mp3', 'audio_codec': 'mp3', 'bitrate': '192k'},
                'aac': {'container': 'aac', 'audio_codec': 'aac', 'bitrate': '192k'},
                'wav': {'container': 'wav', 'audio_codec': 'pcm_s16le'},
                'flac': {'container': 'flac', 'audio_codec': 'flac'},
                'ogg': {'container': 'ogg', 'audio_codec': 'libvorbis', 'bitrate': '192k'},
            }
    
    def convert_format(self, media_info: MediaInfo, output_path: str, 
                      target_format: str) -> bool:
        """Convert media to different format"""
        
        format_options = self.get_format_options(media_info)
        
        if target_format.lower() not in format_options:
            self.logger.error(f"Unsupported target format: {target_format}")
            return False
        
        format_config = format_options[target_format.lower()]
        cmd = ['ffmpeg', '-i', media_info.filepath]
        
        if media_info.has_video:
            # Video codec
            video_codec = format_config['video_codec']
            cmd.extend(['-c:v', video_codec])
            
            # Add NVENC specific settings
            if video_codec.endswith('_nvenc'):
                cmd.extend(['-preset', 'fast'])
            elif video_codec == 'libx264':
                cmd.extend(['-preset', 'fast', '-crf', '23'])
            elif video_codec == 'libvpx-vp9':
                cmd.extend(['-crf', '30', '-b:v', '0'])
            
            # Audio codec (if audio present)
            if media_info.has_audio and 'audio_codec' in format_config:
                audio_codec = format_config['audio_codec']
                cmd.extend(['-c:a', audio_codec])
                
                # Add bitrate for lossy audio codecs
                if 'bitrate' in format_config:
                    cmd.extend(['-b:a', format_config['bitrate']])
        
        elif media_info.has_audio:
            # Audio only conversion
            cmd.extend(['-vn'])  # No video
            audio_codec = format_config['audio_codec']
            cmd.extend(['-c:a', audio_codec])
            
            # Add bitrate for lossy formats
            if 'bitrate' in format_config:
                cmd.extend(['-b:a', format_config['bitrate']])
        
        cmd.extend(['-y', output_path])
        
        return self.run_ffmpeg_command(cmd, f"Converting to {target_format.upper()}")
    
    def extract_audio(self, media_info: MediaInfo, output_path: str, 
                     format: str = 'mp3', bitrate: str = '192k') -> bool:
        """Extract audio from video file"""
        
        if not media_info.has_audio:
            self.logger.error("No audio stream found in the file")
            return False
        
        cmd = [
            'ffmpeg', '-i', media_info.filepath,
            '-vn',  # No video
            '-c:a', 'mp3' if format == 'mp3' else 'aac',
            '-b:a', bitrate,
            '-y', output_path
        ]
        
        return self.run_ffmpeg_command(cmd, "Extracting audio")
    
    def optimize_for_streaming(self, media_info: MediaInfo, output_path: str) -> bool:
        """Optimize video for web streaming"""
        
        if not media_info.has_video:
            self.logger.error("Cannot optimize audio-only file for streaming")
            return False
        
        # Target resolution based on input
        width, height = media_info.resolution or (1920, 1080)
        
        if width > 1920:
            target_res = "1920:1080"
        elif width > 1280:
            target_res = "1280:720"
        else:
            target_res = f"{width}:{height}"
        
        cmd = ['ffmpeg', '-i', media_info.filepath]
        
        if self.use_gpu and self.has_nvenc:
            cmd.extend([
                '-c:v', 'h264_nvenc',
                '-preset', 'fast',
                '-profile:v', 'main',
                '-level', '4.0',
                '-cq', '25'
            ])
        else:
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-profile:v', 'main',
                '-level', '4.0',
                '-crf', '25'
            ])
        
        cmd.extend([
            '-vf', f'scale={target_res}',
            '-r', '30',  # 30 FPS max
            '-movflags', '+faststart',  # Web optimization
            '-c:a', 'aac',
            '-b:a', '128k',
            '-y', output_path
        ])
        
        return self.run_ffmpeg_command(cmd, "Optimizing for streaming")
    
    def reduce_quality(self, media_info: MediaInfo, output_path: str,
                      quality_level: str = "medium") -> bool:
        """Reduce video/audio quality to decrease file size"""
        
        quality_settings = {
            'light': {'video_crf': '28', 'audio_bitrate': '128k', 'scale': None},
            'medium': {'video_crf': '32', 'audio_bitrate': '96k', 'scale': '-1:720'},
            'heavy': {'video_crf': '35', 'audio_bitrate': '64k', 'scale': '-1:480'}
        }
        
        settings = quality_settings.get(quality_level, quality_settings['medium'])
        
        cmd = ['ffmpeg', '-i', media_info.filepath]
        
        if media_info.has_video:
            if self.use_gpu and self.has_nvenc:
                cmd.extend(['-c:v', 'h264_nvenc', '-cq', settings['video_crf']])
            else:
                cmd.extend(['-c:v', 'libx264', '-crf', settings['video_crf']])
            
            if settings['scale']:
                cmd.extend(['-vf', f'scale={settings["scale"]}'])
        
        if media_info.has_audio:
            cmd.extend(['-c:a', 'aac', '-b:a', settings['audio_bitrate']])
        
        cmd.extend(['-y', output_path])
        
        return self.run_ffmpeg_command(cmd, f"Reducing quality ({quality_level})")
    
    def generate_thumbnail(self, media_info: MediaInfo, output_path: str,
                          timestamp: str = "00:00:05") -> bool:
        """Generate thumbnail from video"""
        
        if not media_info.has_video:
            self.logger.error("Cannot generate thumbnail from audio-only file")
            return False
        
        cmd = [
            'ffmpeg', '-i', media_info.filepath,
            '-ss', timestamp,
            '-vframes', '1',
            '-vf', 'scale=320:240',
            '-y', output_path
        ]
        
        return self.run_ffmpeg_command(cmd, "Generating thumbnail")
    
    def select_output_format(self, media_info: MediaInfo) -> Optional[str]:
        """Interactive format selection menu"""
        format_options = self.get_format_options(media_info)
        
        print("\n📋 Available output formats:")
        print("-" * 30)
        
        current_ext = Path(media_info.filepath).suffix.lower().lstrip('.')
        
        formats_list = list(format_options.keys())
        for i, fmt in enumerate(formats_list, 1):
            current_indicator = " (current)" if fmt == current_ext else ""
            description = ""
            
            if media_info.has_video:
                video_codec = format_options[fmt]['video_codec']
                audio_codec = format_options[fmt].get('audio_codec', 'none')
                if video_codec.endswith('_nvenc'):
                    description = f" - GPU accelerated ({video_codec})"
                else:
                    description = f" - {video_codec.upper()}"
            else:
                audio_codec = format_options[fmt]['audio_codec']
                bitrate = format_options[fmt].get('bitrate', 'lossless')
                description = f" - {audio_codec.upper()} ({bitrate})"
            
            print(f"{i}. {fmt.upper()}{current_indicator}{description}")
        
        try:
            choice = input(f"\n👉 Select format (1-{len(formats_list)}) or Enter to cancel: ").strip()
            if not choice:
                return None
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(formats_list):
                return formats_list[choice_idx]
            else:
                print("❌ Invalid selection")
                return None
        except ValueError:
            print("❌ Invalid input")
            return None
    
    def run_ffmpeg_command(self, cmd: List[str], operation: str) -> bool:
        """Execute FFmpeg command with progress monitoring"""
        
        self.logger.info(f"Starting: {operation}")
        self.logger.info(f"Command: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor progress
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    # Extract progress info from FFmpeg output
                    if 'time=' in output:
                        print(f"\r⚡ {operation}... {output.strip()}", end='', flush=True)
            
            process.wait()
            
            if process.returncode == 0:
                print(f"\n✅ {operation} completed successfully!")
                return True
            else:
                error_output = process.stderr.read()
                self.logger.error(f"FFmpeg error: {error_output}")
                print(f"\n❌ {operation} failed!")
                return False
                
        except Exception as e:
            self.logger.error(f"Error running FFmpeg: {e}")
            print(f"\n❌ {operation} failed: {e}")
            return False
    
    def interactive_menu(self, filepath: str):
        """Interactive menu for media processing"""
        
        try:
            # Analyze the media file
            print("🔍 Analyzing media file...")
            media_info = self.analyze_media(filepath)
            self.print_media_info(media_info)
            
            while True:
                # Generate options based on media analysis
                options = self.get_processing_options(media_info)
                
                print(f"\n🎬 Processing Options for {os.path.basename(filepath)}:")
                print("-" * 50)
                
                for key, description in options.items():
                    print(f"{key}. {description}")
                
                choice = input("\n👉 Select an option: ").strip()
                
                if choice == '0':
                    print("👋 Goodbye!")
                    break
                
                if choice not in options:
                    print("❌ Invalid option. Please try again.")
                    continue
                
                # Generate output filename
                base_name = Path(filepath).stem
                output_dir = Path(filepath).parent
                
                success = False
                
                if choice == '1':  # Compress
                    level = input("Compression level (light/medium/heavy) [medium]: ").strip() or "medium"
                    output_path = output_dir / f"{base_name}_compressed.mp4"
                    success = self.compress_video(media_info, str(output_path), level)
                
                elif choice == '2':  # Quality reduction or audio conversion
                    if media_info.has_video:
                        level = input("Quality reduction (light/medium/heavy) [medium]: ").strip() or "medium"
                        output_path = output_dir / f"{base_name}_reduced.mp4"
                        success = self.reduce_quality(media_info, str(output_path), level)
                    else:
                        # Audio format conversion
                        target_format = self.select_output_format(media_info)
                        if target_format:
                            output_path = output_dir / f"{base_name}_converted.{target_format}"
                            success = self.convert_format(media_info, str(output_path), target_format)
                        else:
                            print("❌ Format conversion cancelled")
                            success = False
                
                elif choice == '3':  # Streaming optimization or audio quality
                    if media_info.has_video:
                        output_path = output_dir / f"{base_name}_streaming.mp4"
                        success = self.optimize_for_streaming(media_info, str(output_path))
                    else:
                        level = input("Quality reduction (light/medium/heavy) [medium]: ").strip() or "medium"
                        output_path = output_dir / f"{base_name}_reduced.mp3"
                        success = self.reduce_quality(media_info, str(output_path), level)
                
                elif choice == '4':  # Format conversion
                    target_format = self.select_output_format(media_info)
                    if target_format:
                        output_path = output_dir / f"{base_name}_converted.{target_format}"
                        success = self.convert_format(media_info, str(output_path), target_format)
                    else:
                        print("❌ Format conversion cancelled")
                        success = False
                
                elif choice == '5':  # Extract audio
                    format_choice = input("Audio format (mp3/aac) [mp3]: ").strip() or "mp3"
                    bitrate = input("Audio bitrate (128k/192k/256k) [192k]: ").strip() or "192k"
                    output_path = output_dir / f"{base_name}_audio.{format_choice}"
                    success = self.extract_audio(media_info, str(output_path), format_choice, bitrate)
                
                elif choice == '6':  # Generate thumbnail
                    timestamp = input("Timestamp for thumbnail (HH:MM:SS) [00:00:05]: ").strip() or "00:00:05"
                    output_path = output_dir / f"{base_name}_thumb.jpg"
                    success = self.generate_thumbnail(media_info, str(output_path), timestamp)
                
                elif choice == '7':  # Show metadata
                    cmd = ['ffprobe', '-v', 'quiet', '-show_format', '-show_streams', filepath]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    print("\n📋 Detailed Metadata:")
                    print("-" * 40)
                    print(result.stdout)
                    success = True
                
                if success and choice != '7':
                    print(f"📁 Output saved: {output_path}")
                
                input("\nPress Enter to continue...")
        
        except Exception as e:
            self.logger.error(f"Error in interactive menu: {e}")
            print(f"❌ Error: {e}")

def main():
    """Main entry point"""
    
    print("🎬 Advanced Media Processor")
    print("=" * 40)
    
    if len(sys.argv) != 2:
        print("Usage: python media_processor.py <media_file>")
        print("Supported formats:")
        print("  Video: .mp4, .avi, .mkv, .mov, .webm, .flv, .wmv, .m4v")
        print("  Audio: .mp3, .wav, .flac, .aac, .ogg, .m4a, .wma")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    
    # Initialize processor
    processor = MediaProcessor(use_gpu=True)
    
    # Start interactive processing
    processor.interactive_menu(filepath)

if __name__ == "__main__":
    main()