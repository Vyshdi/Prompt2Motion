from flask import Flask, render_template, send_from_directory, jsonify, request
import os
import sys

BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'frontend')
MANIM_OUTPUT_DIR = os.path.join(BACKEND_DIR, 'manim_scenes')

# FIXED IMPORT (removed 'backend.' because you're already in backend/)
try:
    from render_manim import render_scene
except ImportError as e:
    print(f"Error importing render_manim: {e}")
    exit()
print("FRONTEND_DIR:", FRONTEND_DIR)
app = Flask(__name__,
            template_folder=FRONTEND_DIR,
            static_folder=FRONTEND_DIR,
            static_url_path='')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/generate-animation', methods=['POST'])
def generate_animation_api():
    try:
        data = request.get_json()
        prompt_text = data.get('prompt') if data else "a default green circle"

        if not prompt_text:
            prompt_text = "a default yellow square"
            print("Received empty prompt, using default.")
        
        print(f"Received prompt for animation: '{prompt_text}'")

        absolute_video_path = render_scene(prompt_text)

        if absolute_video_path and os.path.exists(absolute_video_path):
            relative_to_manim_output_dir = os.path.relpath(absolute_video_path, MANIM_OUTPUT_DIR)
            video_url = f"/generated_media/{relative_to_manim_output_dir.replace(os.sep, '/')}"

            return jsonify({'success': True, 'video_url': video_url, 'message': 'Animation generated successfully!'})
        else:
            print("render_scene did not return a valid path or file does not exist.")
            error_message = "Failed to generate Manim script from prompt or rendering failed." \
                            if not absolute_video_path \
                            else "Failed to generate animation video (file not found post-render)."
            return jsonify({'success': False, 'message': error_message}), 500

    except Exception as e:
        print(f"Error in generate_animation_api: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@app.route('/generated_media/<path:filename>')
def serve_generated_media(filename):
    print(f"Attempting to serve generated media: {filename} from {MANIM_OUTPUT_DIR}")
    return send_from_directory(MANIM_OUTPUT_DIR, filename)

if __name__ == '__main__':
    os.makedirs(os.path.join(MANIM_OUTPUT_DIR, "media", "videos"), exist_ok=True)
    app.run(debug=True, use_reloader=False, port=5000)
