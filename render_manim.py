# backend/render_manim.py

import subprocess
import os
import sys
import shutil
import time
import json
import requests
import math

GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"

BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
MANIM_SCENES_DIR = os.path.join(BACKEND_DIR, 'manim_scenes')

def get_animation_params_from_llm(user_prompt):
    if GROQ_API_KEY == "YOUR_GROQ_API_KEY" or not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY is not set. Using fallback.")
        return {"shape": "Circle", "color": "ORANGE", "animation_type": "Create", "error": "API Key not set. Using fallback."}

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    system_prompt_content = """
You are an expert Manim animation assistant. Your task is to interpret a user's animation request
and extract parameters for a 2D animation. Your response MUST be a VALID JSON object.

**Main Object Parameters:**
1.  "shape": Primary geometric shape. Valid: "Circle", "Square", "Triangle", "Rectangle", "Line", "Dot", "Star", "Polygon". Default: "Circle".
2.  "color": Initial color. Valid Manim colors (e.g., "RED", "BLUE", "GREEN", "YELLOW", "PURPLE", "WHITE"). Default: "WHITE".
3.  "text_content": (If the primary object is text) The string content for a Manim Text mobject.

**Animation Parameters:**
"animations": An array of animation steps. Each step is an object with:
    - "type": The type of animation. Valid types:
        - Appearance: "Create", "FadeIn", "GrowFromCenter", "Write" (for text).
        - Movement: "Move".
        - Transformation: "Rotate", "Scale", "TransformShape", "ChangeColor".
        - Emphasis: "Indicate", "Flash".
        - Grouping: "AnimationGroup".
    - "details": An object containing parameters specific to the animation type.

**Animation Detail Structures:**

* **For "Move":**
    `"movement_details": {"direction": "UP"/"DOWN"/"LEFT"/"RIGHT" OR "UP_THEN_DOWN"/"LEFT_THEN_RIGHT"/"UP_AND_DOWN"/"LEFT_AND_RIGHT", "distance": number (default 1)}`
    Explicitly map "X and Y" or "X then Y" phrases to sequence directions like "UP_THEN_DOWN" or "UP_AND_DOWN".
* **For "Rotate":** `"rotation_details": {"angle_degrees": number (default 90)}`
* **For "Scale":** `"scale_details": {"factor": number (default 2 for grow, 0.5 for shrink)}`
* **For "TransformShape":** `"transform_details": {"target_shape": "ShapeName", "target_color": "COLOR" (optional)}`
* **For "ChangeColor":** `"color_change_details": {"target_color": "COLOR"}`
* **For "Indicate" / "Flash":** Optional `{"flash_color": "COLOR"}` for Flash.
* **For "AnimationGroup":** `"grouped_animations": [ { "type": "...", "details": {...} }, { ... } ]`

**General Guidelines:**
- If multiple distinct actions are sequential, create multiple animation step objects in "animations".
- If actions should happen together, use "AnimationGroup".

**Examples:**
1.  User: "A red square appears, then moves up by 2, then turns blue."
    JSON: {"shape": "Square", "color": "RED", "animations": [{"type": "Create"}, {"type": "Move", "details": {"movement_details": {"direction": "UP", "distance": 2}}}, {"type": "ChangeColor", "details": {"color_change_details": {"target_color": "BLUE"}}}]}
2.  User: "A yellow circle. Rotate it 180 degrees and make it twice as big at the same time."
    JSON: {"shape": "Circle", "color": "YELLOW", "animations": [{"type": "Create"}, {"type": "AnimationGroup", "details": {"grouped_animations": [{"type": "Rotate", "details": {"rotation_details": {"angle_degrees": 180}}}, {"type": "Scale", "details": {"scale_details": {"factor": 2}}}]}}]}
3.  User: "Write 'Hello Manim' in green, then make it flash."
    JSON: {"text_content": "Hello Manim", "color": "GREEN", "animations": [{"type": "Write"}, {"type": "Flash", "details": {"flash_details": {"flash_color": "WHITE"}}}]}
4.  User: "Transform a blue triangle into a red square."
    JSON: {"shape": "Triangle", "color": "BLUE", "animations": [{"type": "Create"}, {"type": "TransformShape", "details": {"transform_details": {"target_shape": "Square", "target_color": "RED"}}}]}
5.  User: "a purple circle moving up and down"
    JSON: {"shape": "Circle", "color": "PURPLE", "animations": [{"type": "Create"}, {"type": "Move", "details": {"movement_details": {"direction": "UP_AND_DOWN", "distance": 1}}}]}
6.  User: "a line that moves left then right"
    JSON: {"shape": "Line", "color": "WHITE", "animations": [{"type": "Create"}, {"type": "Move", "details": {"movement_details": {"direction": "LEFT_THEN_RIGHT", "distance": 1}}}]}

If unclear or too complex, return {"error": "Prompt is too complex or ambiguous."}
"""
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "system", "content": system_prompt_content}, {"role": "user", "content": user_prompt}],
        "temperature": 0.1, "max_tokens": 1200, "response_format": {"type": "json_object"}
    }
    print(f"Sending prompt to Groq LLM: '{user_prompt}'")
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        llm_response_json = response.json()
        if llm_response_json.get("choices") and llm_response_json["choices"][0].get("message"):
            content_str = llm_response_json["choices"][0]["message"].get("content")
            if content_str:
                try:
                    parsed_params = json.loads(content_str)
                    print(f"LLM JSON Response (parsed): {json.dumps(parsed_params, indent=2)}")
                    return parsed_params
                except json.JSONDecodeError as e:
                    print(f"Error: LLM response not valid JSON: {content_str}\nError: {e}")
                    return {"error": f"LLM response not valid JSON. Details: {e}"}
            else:
                print("Error: LLM response content is empty.")
                return {"error": "LLM response content is empty."}
        else:
            error_detail = llm_response_json.get("error", {}).get("message", "Unknown LLM error.")
            print(f"Error: Unexpected LLM response. Detail: {error_detail}. Full: {llm_response_json}")
            return {"error": f"Unexpected LLM response: {error_detail}"}
    except requests.exceptions.Timeout:
        print("Error: Groq API request timed out.")
        return {"error": "API request timed out."}
    except requests.exceptions.RequestException as e:
        print(f"Error calling Groq API: {e}")
        return {"error": f"API request failed: {e}"}
    except Exception as e:
        print(f"An unexpected error occurred during LLM call: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Unexpected error during LLM call: {e}"}

def generate_manim_script_from_prompt(prompt_text):
    print(f"Processing prompt with LLM for advanced actions: '{prompt_text}'")
    llm_data = get_animation_params_from_llm(prompt_text)

    llm_error_message = None
    if not llm_data or llm_data.get("error"):
        print(f"Failed to get valid parameters from LLM. Error: {llm_data.get('error', 'Unknown LLM error')}")
        initial_shape_type = "Circle"
        initial_color_name = "GRAY"
        initial_text_content = None
        animation_steps_data = [{"type": "Create"}]
        llm_error_message = llm_data.get('error', 'LLM processing failed')
    else:
        initial_shape_type = llm_data.get("shape", "Circle")
        initial_color_name = llm_data.get("color", "WHITE").upper()
        initial_text_content = llm_data.get("text_content")
        animation_steps_data = llm_data.get("animations", [{"type": "Create"}])

    timestamp_ms = int(time.time() * 1000)
    scene_class_name = f"AdvancedScene_{timestamp_ms}"

    valid_color_names = ["RED", "GREEN", "BLUE", "YELLOW", "ORANGE", "PURPLE", "PINK", "WHITE", "BLACK", "GRAY", "LIGHT_GRAY", "DARK_GRAY"]
    if initial_color_name not in valid_color_names: initial_color_name = "WHITE"

    initial_shape_class_name = initial_shape_type.capitalize()
    valid_shape_class_names = ["Circle", "Square", "Triangle", "Rectangle", "Line", "Dot", "Star", "Polygon"]
    if initial_shape_class_name not in valid_shape_class_names: initial_shape_class_name = "Circle"

    if initial_text_content:
        escaped_text = json.dumps(initial_text_content) 
        initial_object_code = f"Text({escaped_text}, color={initial_color_name})"
        main_object_var_name = "main_text_obj"
    else:
        if initial_shape_class_name == "Polygon":
             initial_object_code = f"Polygon(*[[0,1,0], [-1,-0.5,0], [1,-0.5,0]], color={initial_color_name})"
        elif initial_shape_class_name == "Star":
             initial_object_code = f"Star(n=5, outer_radius=1, inner_radius=0.5, color={initial_color_name})"
        else:
             initial_object_code = f"{initial_shape_class_name}(color={initial_color_name})"
        main_object_var_name = "main_shape_obj"

    if llm_error_message is None:
        llm_error_msg_for_script = "None"
    else:
        llm_error_msg_for_script = json.dumps(str(llm_error_message)) 

    animation_plays_code_list = []
    initial_creation_done = False
    
    if not animation_steps_data: # Ensure there's at least a create if LLM returns empty animations
        animation_steps_data = [{"type": "Create"}]

    first_anim_type = animation_steps_data[0].get("type")
    
    if initial_text_content and first_anim_type != "Write":
        # If main object is text, and first anim isn't Write, assume we need to Write it first.
        animation_plays_code_list.append(f"self.play(Write({main_object_var_name}))")
        initial_creation_done = True
    elif not initial_text_content and first_anim_type not in ["Create", "FadeIn", "GrowFromCenter"]:
        animation_plays_code_list.append(f"self.play(Create({main_object_var_name}))")
        initial_creation_done = True

    for anim_step in animation_steps_data:
        anim_type = anim_step.get("type")
        details = anim_step.get("details", {}) # Ensure details is always a dict
        current_anim_code = ""

        if anim_type == "Create" and not initial_creation_done:
            current_anim_code = f"self.play(Create({main_object_var_name}))"
            initial_creation_done = True
        elif anim_type == "FadeIn" and not initial_creation_done:
            current_anim_code = f"self.play(FadeIn({main_object_var_name}))"
            initial_creation_done = True
        elif anim_type == "GrowFromCenter" and not initial_creation_done:
            current_anim_code = f"self.play(GrowFromCenter({main_object_var_name}))"
            initial_creation_done = True
        elif anim_type == "Write" and initial_text_content and not initial_creation_done:
            current_anim_code = f"self.play(Write({main_object_var_name}))"
            initial_creation_done = True
        
        elif anim_type == "Move":
            move_details = details.get("movement_details", {})
            direction = move_details.get("direction", "RIGHT").upper()
            distance = float(move_details.get("distance", 1))
            
            if direction in ["UP_THEN_DOWN", "UP_AND_DOWN"]:
                current_anim_code = (f"self.play({main_object_var_name}.animate.shift(UP*{distance}))\n"
                                     f"        self.wait(0.3)\n"
                                     f"        self.play({main_object_var_name}.animate.shift(DOWN*{distance}*2))\n"
                                     f"        self.wait(0.3)\n"
                                     f"        self.play({main_object_var_name}.animate.shift(UP*{distance}))")
            elif direction in ["LEFT_THEN_RIGHT", "LEFT_AND_RIGHT"]:
                current_anim_code = (f"self.play({main_object_var_name}.animate.shift(LEFT*{distance}))\n"
                                     f"        self.wait(0.3)\n"
                                     f"        self.play({main_object_var_name}.animate.shift(RIGHT*{distance}*2))\n"
                                     f"        self.wait(0.3)\n"
                                     f"        self.play({main_object_var_name}.animate.shift(LEFT*{distance}))")
            elif direction in ["UP", "DOWN", "LEFT", "RIGHT", "UP_LEFT", "UP_RIGHT", "DOWN_LEFT", "DOWN_RIGHT"]:
                 current_anim_code = f"self.play({main_object_var_name}.animate.shift({direction}*{distance}))"
            else:
                print(f"Warning: Unknown movement direction '{direction}'. Skipping move.")


        elif anim_type == "Rotate":
            rot_details = details.get("rotation_details", {})
            angle_deg = float(rot_details.get("angle_degrees", 90))
            current_anim_code = f"self.play(Rotate({main_object_var_name}, angle=math.radians({angle_deg:.2f})))"

        elif anim_type == "Scale":
            scale_details = details.get("scale_details", {})
            factor = float(scale_details.get("factor", 2))
            current_anim_code = f"self.play({main_object_var_name}.animate.scale({factor:.2f}))"

        elif anim_type == "ChangeColor":
            cc_details = details.get("color_change_details", {})
            target_color_name = cc_details.get("target_color", "WHITE").upper()
            if target_color_name not in valid_color_names: target_color_name = "WHITE"
            current_anim_code = f"self.play({main_object_var_name}.animate.set_color({target_color_name}))"

        elif anim_type == "TransformShape":
            ts_details = details.get("transform_details", {})
            target_shape_class = ts_details.get("target_shape", "Square").capitalize()
            if target_shape_class not in valid_shape_class_names: target_shape_class = "Square"
            
            target_color_name_from_details = ts_details.get("target_color")
            if target_color_name_from_details:
                target_color_name = target_color_name_from_details.upper()
                if target_color_name not in valid_color_names: target_color_name = initial_color_name
            else: # If target_color not in details, use the object's current color (conceptually) or initial
                target_color_name = initial_color_name # Simplified: use initial color of main object

            if target_shape_class == "Polygon":
                 target_mobject_code = f"Polygon(*[[0,1,0], [-0.5,-1,0], [0.5,-1,0]], color={target_color_name})"
            elif target_shape_class == "Star":
                 target_mobject_code = f"Star(color={target_color_name})"
            else:
                 target_mobject_code = f"{target_shape_class}(color={target_color_name})"
            
            animation_plays_code_list.append(f"target_obj = {target_mobject_code}")
            current_anim_code = f"self.play(Transform({main_object_var_name}, target_obj))"
            
        elif anim_type == "Indicate":
            current_anim_code = f"self.play(Indicate({main_object_var_name}))"
        elif anim_type == "Flash":
            flash_details = details.get("flash_details", {})
            flash_color = flash_details.get("flash_color", "YELLOW").upper()
            if flash_color not in valid_color_names: flash_color = "YELLOW"
            current_anim_code = f"self.play(Flash({main_object_var_name}, color={flash_color}))"
        
        elif anim_type == "AnimationGroup":
            grouped_anims_data = details.get("grouped_animations", [])
            manim_group_anims_list = []
            for group_anim_step in grouped_anims_data:
                group_anim_type = group_anim_step.get("type")
                group_details_data = group_anim_step.get("details", {}) # Ensure this is used
                
                if group_anim_type == "Rotate":
                    rot_details = group_details_data.get("rotation_details", {})
                    angle_deg = float(rot_details.get("angle_degrees", 90))
                    manim_group_anims_list.append(f"Rotate({main_object_var_name}, angle=math.radians({angle_deg:.2f}))")
                elif group_anim_type == "Scale":
                    scale_details = group_details_data.get("scale_details", {})
                    factor = float(scale_details.get("factor", 2))
                    manim_group_anims_list.append(f"{main_object_var_name}.animate.scale({factor:.2f})")
                elif group_anim_type == "ChangeColor":
                    cc_details = group_details_data.get("color_change_details", {})
                    target_color_name = cc_details.get("target_color", "WHITE").upper()
                    if target_color_name not in valid_color_names: target_color_name = "WHITE"
                    manim_group_anims_list.append(f"{main_object_var_name}.animate.set_color({target_color_name})")
                # Add more anim types that can be grouped and use their respective 'details' sub-keys
            if manim_group_anims_list:
                current_anim_code = f"self.play(AnimationGroup({', '.join(manim_group_anims_list)}, lag_ratio=0))" # lag_ratio=0 for true simultaneous

        if current_anim_code:
            animation_plays_code_list.append(current_anim_code)

    animation_plays_code_str = "\n        ".join(animation_plays_code_list) if animation_plays_code_list else "self.wait(1)"

    script_content = f"""
from manim import Scene, Circle, Square, Triangle, Rectangle, Line, Dot, Star, Polygon
from manim import Create, FadeIn, GrowFromCenter, Write, Transform, Indicate, Flash, Rotate, AnimationGroup, MoveAlongPath
from manim import RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, PINK, WHITE, BLACK, GRAY, LIGHT_GRAY, DARK_GRAY
from manim import UP, DOWN, LEFT, RIGHT, ORIGIN, PI, UL, UR, DL, DR 
from manim import Text, Tex
import math

class {scene_class_name}(Scene):
    def construct(self):
        llm_error_msg_str = {llm_error_msg_for_script} 

        if llm_error_msg_str is not None:
            error_display_text = f"LLM Error: {{llm_error_msg_str}}" 
            error_text_mobject = Text(error_display_text, font_size=24, color=RED)
            self.play(Write(error_text_mobject))
            self.wait(3)
            return

        try:
            {main_object_var_name} = {initial_object_code}
        except Exception as e_obj_create:
            obj_creation_error_text = f"Object Creation Error: {{str(e_obj_create)}} \\nCode: {initial_object_code}"
            error_text = Text(obj_creation_error_text, font_size=24, color=RED)
            self.play(Write(error_text))
            self.wait(2)
            return
        
        {animation_plays_code_str}
        
        self.wait(1)
"""
    print(f"Generated Manim script for scene: {scene_class_name}")
    return script_content, scene_class_name

def clear_scene_specific_cache_and_output(scene_file_name_without_ext, base_dir=MANIM_SCENES_DIR):
    scene_media_output_dir = os.path.join(base_dir, "media", "videos", scene_file_name_without_ext)
    if os.path.exists(scene_media_output_dir):
        try: shutil.rmtree(scene_media_output_dir)
        except Exception as e: print(f"Warning: Could not clear dir {scene_media_output_dir}: {e}")

def render_scene(prompt_text="a default white circle"):
    script_content, scene_class_name = generate_manim_script_from_prompt(prompt_text)
    if not script_content or not scene_class_name: return None
    dynamic_scene_file_basename = f"{scene_class_name.lower()}.py"
    dynamic_scene_file_path = os.path.join(MANIM_SCENES_DIR, dynamic_scene_file_basename)
    try:
        with open(dynamic_scene_file_path, "w", encoding="utf-8") as f: f.write(script_content)
    except IOError as e: print(f"Error writing script: {e}"); return None
    
    scene_file_name_without_ext = os.path.splitext(dynamic_scene_file_basename)[0]
    clear_scene_specific_cache_and_output(scene_file_name_without_ext, MANIM_SCENES_DIR)

    manim_executable_cmd = "manim"
    current_env = os.environ.copy()
    try: subprocess.run([manim_executable_cmd, "--version"], check=True, capture_output=True, env=current_env, timeout=5)
    except: manim_executable_cmd = [sys.executable, "-m", "manim"]
    command = [*([manim_executable_cmd] if isinstance(manim_executable_cmd, str) else manim_executable_cmd), "-ql", dynamic_scene_file_basename, scene_class_name]
    
    print(f"Running Manim: {' '.join(command)} (CWD: {MANIM_SCENES_DIR})")
    try:
        process = subprocess.run(command, capture_output=True, text=True, check=True, cwd=MANIM_SCENES_DIR, env=current_env, timeout=90)
        print("\nManim STDOUT:", process.stdout, "\nManim rendering successful!")
        expected_video_path = os.path.join(MANIM_SCENES_DIR, "media", "videos", scene_file_name_without_ext, "480p15", f"{scene_class_name}.mp4")
        if os.path.exists(expected_video_path):
            print(f"Video file created at: {expected_video_path}")
            return expected_video_path
        else: 
            print(f"Video file NOT found at expected path: {expected_video_path}. Searching...")
            media_dir = os.path.join(MANIM_SCENES_DIR, "media", "videos", scene_file_name_without_ext)
            if os.path.isdir(media_dir):
                for root, _, files_in_walk in os.walk(media_dir): 
                    for f_name_walk in files_in_walk:  
                        if f_name_walk.endswith(f"{scene_class_name}.mp4"): 
                            found_path = os.path.join(root, f_name_walk) 
                            print(f"Found video file at: {found_path}")
                            return found_path
            print(f"Could not automatically locate the output video file in {media_dir}.")
            return None
    except subprocess.CalledProcessError as e:
        print("\nError during Manim rendering (subprocess.CalledProcessError):")
        print("Command:", ' '.join(e.cmd)); print("Return code:", e.returncode)
        print("STDOUT:", e.stdout); print("STDERR:", e.stderr)
        return None
    except subprocess.TimeoutExpired as e:
        print("\nManim rendering timed out.")
        cmd_str = ' '.join(e.cmd) if hasattr(e, 'cmd') and e.cmd else ' '.join(command)
        stdout_str = e.stdout.decode(errors='ignore') if hasattr(e, 'stdout') and e.stdout else ""
        stderr_str = e.stderr.decode(errors='ignore') if hasattr(e, 'stderr') and e.stderr else ""
        print(f"Command: {cmd_str}"); print(f"STDOUT: {stdout_str}"); print(f"STDERR: {stderr_str}")
        return None
    except FileNotFoundError:
        executable_str = manim_executable_cmd if isinstance(manim_executable_cmd, str) else ' '.join(manim_executable_cmd)
        print(f"Error: Manim command ('{executable_str}') not found.")
        return None
    finally:
        pass

if __name__ == '__main__':
    test_prompt = input("Enter a test prompt for LLM (e.g., 'red square appears, then moves up and down, then turns blue and rotates 90 degrees'): ")
    if not test_prompt:
        test_prompt = "a green triangle that grows from center, then scales by 0.5, then flashes yellow, then moves left and right"
    
    print(f"\n--- Testing render_scene with LLM prompt: '{test_prompt}' ---")
    if GROQ_API_KEY == "YOUR_GROQ_API_KEY" or not GROQ_API_KEY:
        print("\nWARNING: GROQ_API_KEY is not set. LLM call will be skipped/use fallback.")

    output_file = render_scene(test_prompt)
    if output_file:
        print(f"\n--- Test successful! Video generated: {output_file} ---")
        try:
            if sys.platform == "win32": os.startfile(output_file)
            elif sys.platform == "darwin": subprocess.call(["open", output_file])
            else: subprocess.call(["xdg-open", output_file])
        except Exception as e: print(f"Could not auto-open video: {e}")
    else:
        print("\n--- Test failed. Review Manim output above. ---")
