import os
import ffmpeg
from config import Config

class VideoMerger:
    def __init__(self):
        self.download_dir = Config.DOWNLOAD_DIR
        
    async def merge_videos(self, video_files, output_name, progress_callback=None):
        try:
            # Create a temporary file list
            list_file = os.path.join(self.download_dir, "files.txt")
            with open(list_file, "w") as f:
                for video in video_files:
                    f.write(f"file '{video}'\n")
            
            output_path = os.path.join(self.download_dir, f"{output_name}.mp4")
            
            # Use ffmpeg-python for merging
            stream = ffmpeg.input(list_file, format='concat', safe=0)
            stream = ffmpeg.output(stream, output_path, c='copy')
            
            # Run the ffmpeg command
            ffmpeg.run(stream, overwrite_output=True)
            
            # Clean up
            os.remove(list_file)
            for video in video_files:
                if os.path.exists(video):
                    os.remove(video)
                    
            return output_path
            
        except Exception as e:
            print(f"Error merging videos: {str(e)}")
            return None
    
    @staticmethod
    def get_video_info(file_path):
        try:
            probe = ffmpeg.probe(file_path)
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            
            return {
                'duration': float(probe['format']['duration']),
                'width': int(video_info['width']),
                'height': int(video_info['height']),
                'codec': video_info['codec_name']
            }
        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            return None 