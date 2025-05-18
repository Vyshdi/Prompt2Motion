# backend/manim_scenes/intro_scene.py

from manim import Scene, Circle, Create, RED

class IntroScene(Scene):
    def construct(self):
        # Create a red circle
        red_circle = Circle(color=RED, fill_opacity=0.5)

        # Show the circle being created
        self.play(Create(red_circle))

        # Wait for a couple of seconds
        self.wait(2)
