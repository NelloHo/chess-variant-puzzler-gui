import os
import subprocess
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from kivy.clock import Clock, mainthread
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, RoundedRectangle

Window.size = (900, 700)


class HighlightedCheckBox(CheckBox):
    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint', (None, None))
        kwargs.setdefault('size', (52, 52))
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 0.25)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[6])
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


class FileChooserPopup(Popup):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.title = "Select File"
        self.size_hint = (0.9, 0.9)
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.filechooser = FileChooserIconView()
        layout.add_widget(self.filechooser)
        
        btn_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        select_btn = Button(text='Select')
        select_btn.bind(on_press=self.select_file)
        cancel_btn = Button(text='Cancel')
        cancel_btn.bind(on_press=self.dismiss)
        
        btn_layout.add_widget(select_btn)
        btn_layout.add_widget(cancel_btn)
        layout.add_widget(btn_layout)
        
        self.content = layout
    
    def select_file(self, instance):
        if self.filechooser.selection:
            self.callback(self.filechooser.selection[0])
            self.dismiss()


class ChessVariantPuzzlerGUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10
        
        # Theme
        ubuntu_purple = (48/255, 10/255, 36/255, 1)
        light_text = (238/255, 238/255, 236/255, 1)
        Window.clearcolor = ubuntu_purple
        
        title = Label(text='Chess Variant Puzzler GUI', size_hint_y=0.08, font_size='24sp', bold=True, color=light_text)
        self.add_widget(title)
        
        scroll = ScrollView(size_hint=(1, 0.82))
        content = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        
        content.add_widget(self.create_section_header('Engine Configuration'))
        content.add_widget(self.build_engine_config_ui())
        
        content.add_widget(self.create_section_header('1. Generator Options'))
        content.add_widget(self.build_generator_config_ui())

        content.add_widget(self.create_section_header('2. Puzzler Options'))
        content.add_widget(self.build_puzzler_config_ui())
        
        scroll.add_widget(content)
        self.add_widget(scroll)
        
        progress_layout = GridLayout(cols=3, size_hint_y=None, height=60, spacing=10)
        progress_layout.add_widget(Label(text='Generator Progress:', color=light_text, size_hint_x=0.3))
        self.generator_progress = ProgressBar(max=100, size_hint_x=0.4)
        progress_layout.add_widget(self.generator_progress)
        progress_layout.add_widget(Label(text='', size_hint_x=0.3)) # Spacer
        
        progress_layout.add_widget(Label(text='Puzzler Progress:', color=light_text, size_hint_x=0.3))
        self.puzzler_progress = ProgressBar(max=100, size_hint_x=0.4)
        progress_layout.add_widget(self.puzzler_progress)
        progress_layout.add_widget(Label(text='', size_hint_x=0.3)) # Spacer
        self.add_widget(progress_layout)

        self.output_text = TextInput(multiline=True, readonly=True, size_hint_y=0.3, background_color=(0.1, 0.1, 0.1, 1), foreground_color=(0, 1, 0, 1))
        self.add_widget(self.output_text)
        
        run_layout = BoxLayout(size_hint_y=0.1, spacing=10, padding=(0, 5))
        
        pgn_box = BoxLayout(size_hint_x=0.4, spacing=10, padding=(0, 0))
        pgn_box.add_widget(Label(text='Output PGN?', color=light_text))
        self.pgn_checkbox = HighlightedCheckBox()
        self.pgn_checkbox.bind(active=self._on_pgn_checkbox)
        pgn_box.add_widget(self.pgn_checkbox)
        self.pgn_checkbox_label = Label(text='NO', color=light_text, bold=True, size_hint_x=None, width=50)
        pgn_box.add_widget(self.pgn_checkbox_label)
        run_layout.add_widget(pgn_box)

        self.run_button = Button(text='RUN', font_size='20sp', bold=True, background_color=(0.2, 0.6, 0.8, 1))
        self.run_button.bind(on_press=self.run_workflow)
        run_layout.add_widget(self.run_button)

        self.puzzle_count_label = Label(text='Puzzles Generated: 0', size_hint_x=0.3, color=light_text)
        run_layout.add_widget(self.puzzle_count_label)
        
        self.add_widget(run_layout)

    def _on_pgn_checkbox(self, instance, value):
        self.pgn_checkbox_label.text = 'YES' if value else 'NO'

    def build_engine_config_ui(self):
        engine_grid = GridLayout(cols=3, spacing=10, size_hint_y=None, height=120)
        engine_grid.add_widget(Label(text='Engine Path:', size_hint_x=0.3))
        self.engine_path = TextInput(multiline=False, hint_text='/path/to/fairy-stockfish', size_hint_x=0.5)
        engine_grid.add_widget(self.engine_path)
        engine_browse = Button(text='Browse', size_hint_x=0.2)
        engine_browse.bind(on_press=lambda x: self.browse_file(self.engine_path))
        engine_grid.add_widget(engine_browse)
        
        engine_grid.add_widget(Label(text='NNUE File:', size_hint_x=0.3))
        self.nnue_path = TextInput(multiline=False, hint_text='/path/to/nnue/file.nnue', size_hint_x=0.5)
        self.nnue_path.bind(text=self._update_variant_from_nnue) # Bind for real-time update
        engine_grid.add_widget(self.nnue_path)
        nnue_browse = Button(text='Browse', size_hint_x=0.2)
        nnue_browse.bind(on_press=lambda x: self.browse_file(self.nnue_path))
        engine_grid.add_widget(nnue_browse)

        engine_grid.add_widget(Label(text='Variant INI Path:', size_hint_x=0.3))
        self.variant_path = TextInput(text='variants.ini', multiline=False, hint_text='/path/to/variants.ini', size_hint_x=0.5)
        engine_grid.add_widget(self.variant_path)
        variant_browse = Button(text='Browse', size_hint_x=0.2)
        variant_browse.bind(on_press=lambda x: self.browse_file(self.variant_path))
        engine_grid.add_widget(variant_browse)
        return engine_grid

    def _update_variant_from_nnue(self, instance, value):
        # This method will be called when nnue_path text changes
        nnue_file = os.path.basename(instance.text)
        if nnue_file.endswith('.nnue'):
            base_name = nnue_file[:-len('.nnue')]
            variant_name = base_name.split('-')[0]
            if variant_name:
                self.variant.text = variant_name


    def build_generator_config_ui(self):
        gen_grid = GridLayout(cols=2, spacing=10, size_hint_y=None, height=120)
        gen_grid.add_widget(Label(text='Variant:', size_hint_x=0.3))
        self.variant = TextInput(text='chess', multiline=False, size_hint_x=0.7)
        gen_grid.add_widget(self.variant)
        gen_grid.add_widget(Label(text='Positions to Generate:', size_hint_x=0.3))
        self.num_games = TextInput(text='100', multiline=False, input_filter='int', size_hint_x=0.7)
        gen_grid.add_widget(self.num_games)
        gen_grid.add_widget(Label(text='Generated Positions File:', size_hint_x=0.3))
        self.input_file = TextInput(text='positions.epd', multiline=False)
        gen_grid.add_widget(self.input_file)
        return gen_grid

    def build_puzzler_config_ui(self):
        config_grid = GridLayout(cols=2, spacing=10, size_hint_y=None, height=160)
        config_grid.add_widget(Label(text='Depth:', size_hint_x=0.3))
        self.depth = TextInput(text='10', multiline=False, input_filter='int', size_hint_x=0.7)
        config_grid.add_widget(self.depth)
        config_grid.add_widget(Label(text='Threads:', size_hint_x=0.3))
        self.threads = TextInput(text='4', multiline=False, input_filter='int', size_hint_x=0.7)
        config_grid.add_widget(self.threads)
        config_grid.add_widget(Label(text='Hash (MB):', size_hint_x=0.3))
        self.hash_size = TextInput(text='256', multiline=False, input_filter='int', size_hint_x=0.7)
        config_grid.add_widget(self.hash_size)
        config_grid.add_widget(Label(text='Final Puzzles File:', size_hint_x=0.3))
        self.output_file = TextInput(text='puzzles.epd', multiline=False)
        config_grid.add_widget(self.output_file)
        return config_grid

    def create_section_header(self, text):
        return Label(text=text, size_hint_y=None, height=30, bold=True, color=(0.3, 0.6, 1, 1))
    
    def browse_file(self, target_input):
        popup = FileChooserPopup(lambda path: setattr(target_input, 'text', path))
        popup.open()
    
    @mainthread
    def append_output(self, text):
        self.output_text.text += text + '\n'
        self.output_text.cursor = (0, 0)

    @mainthread
    def update_progress(self, progress_bar, value):
        if progress_bar:
            progress_bar.value = value

    @mainthread
    def update_puzzle_count(self, count):
        self.puzzle_count_label.text = f'Puzzles Generated: {count}'

    def run_workflow(self, instance):
        self.run_button.disabled = True
        self.output_text.text = ''
        self.update_puzzle_count(0)
        self.generator_progress.value = 0
        self.puzzler_progress.value = 0
        
        thread = threading.Thread(target=self._workflow_thread)
        thread.daemon = True
        thread.start()

    def _execute_blocking_command(self, cmd, success_msg, progress_bar=None, output_file=None, file_mode='w'):
        self.append_output(f"Running: {' '.join(cmd)}\n")
        process = None
        f_out = None
        app_log = None
        try:
            app_log = open('app.log', 'a', encoding='utf8') # Open app.log in append mode
            app_log.write(f"--- Running: {' '.join(cmd)} ---\n")

            self.update_progress(progress_bar, 0)
            
            process_kwargs = {
                'stderr': subprocess.PIPE,
                'stdout': subprocess.PIPE, # Always capture stdout to pipe
                'text': True,
                'cwd': os.getcwd(),
                'bufsize': 1, # Line-buffered
                'universal_newlines': True
            }

            process = subprocess.Popen(cmd, **process_kwargs)
            
            # Open output file if specified
            if output_file:
                f_out = open(output_file, file_mode, encoding='utf8')

            # Helper to read from pipe and log
            def _read_pipe_and_log(pipe, log_prefix, is_stderr=False):
                for line in iter(pipe.readline, ''):
                    line = line.strip()
                    app_log.write(f"[{log_prefix}] {line}\n") # Write to app.log
                    if is_stderr and '%' in line: # Check for tqdm progress in stderr
                        try:
                            percent = int(line.split('%')[0])
                            self.update_progress(progress_bar, percent)
                        except (ValueError, IndexError):
                            self.append_output(f"[{log_prefix}] {line}")
                    elif line:
                        self.append_output(f"[{log_prefix}] {line}")
                        if log_prefix == "stdout" and f_out: # Write stdout to file if specified
                            f_out.write(line + '\n')

            stdout_thread = threading.Thread(target=_read_pipe_and_log, args=(process.stdout, "stdout", False))
            stderr_thread = threading.Thread(target=_read_pipe_and_log, args=(process.stderr, "stderr", True))

            stdout_thread.daemon = True
            stderr_thread.daemon = True

            stdout_thread.start()
            stderr_thread.start()

            # Wait for the process to terminate
            process.wait()

            # Wait for reader threads to finish processing all output
            stdout_thread.join()
            stderr_thread.join()

            if process.returncode == 0:
                self.append_output(f"\n✓ {success_msg}\n")
                app_log.write(f"✓ {success_msg}\n")
                self.update_progress(progress_bar, 100)
                return True
            else:
                self.append_output(f"\n✗ Command failed with code {process.returncode}\n")
                app_log.write(f"✗ Command failed with code {process.returncode}\n")
                return False
        except Exception as e:
            import traceback
            error_str = f"\n✗ Exception: {str(e)}\n{traceback.format_exc()}"
            self.append_output(error_str)
            if app_log: app_log.write(error_str + '\n')
            return False
        finally:
            if process and process.stdout:
                process.stdout.close()
            if process and process.stderr:
                process.stderr.close()
            if f_out:
                f_out.close()
            if app_log:
                app_log.close()

    def _workflow_thread(self):
        uci_options = []
        if self.threads.text: uci_options.extend(['-o', f'Threads={self.threads.text}'])
        if self.hash_size.text: uci_options.extend(['-o', f'Hash={self.hash_size.text}'])
        if self.nnue_path.text: uci_options.extend(['-o', f'EvalFile={self.nnue_path.text}'])
        if self.variant_path.text: uci_options.extend(['-o', f'VariantPath={self.variant_path.text}'])

        gen_cmd = ['/usr/bin/python3.12', './_internal/generator.py', '--engine', self.engine_path.text, '--variant', self.variant.text, '--count', self.num_games.text] + uci_options
        gen_output_path = self.input_file.text
        success = self._execute_blocking_command(gen_cmd, f"Positions generated to {gen_output_path}", self.generator_progress, output_file=gen_output_path)

        if success:
            puzzler_cmd = ['/usr/bin/python3.12', './_internal/puzzler.py', '--engine', self.engine_path.text, '--variant', self.variant.text, '-d', self.depth.text, self.input_file.text] + uci_options
            puzzler_output_path = self.output_file.text
            success = self._execute_blocking_command(
                puzzler_cmd,
                f"Puzzles extracted to {puzzler_output_path}",
                self.puzzler_progress,
                output_file=puzzler_output_path,
                file_mode='a'
            )
            
            if success:
                try:
                    with open(puzzler_output_path, 'r', encoding='utf8') as f:
                        num_puzzles = sum(1 for line in f if line.strip())
                    self.update_puzzle_count(num_puzzles)
                except Exception as e:
                    self.append_output(f"Error counting puzzles: {e}")

        if success and self.pgn_checkbox.active:
            pgn_input_epd = self.output_file.text
            pgn_output_pgn = pgn_input_epd.replace('.epd', '.pgn')
            pgn_cmd = ['/usr/bin/python3.12', './_internal/pgn.py', pgn_input_epd]
            if self.variant_path.text: pgn_cmd.extend(['-p', self.variant_path.text])
            self._execute_blocking_command(pgn_cmd, f"Converted to {pgn_output_pgn}", output_file=pgn_output_pgn)

        self.run_button.disabled = False


class ChessVariantPuzzlerApp(App):
    def build(self):
        self.title = 'Chess Variant Puzzler'
        self.store = JsonStore('settings.json')
        return ChessVariantPuzzlerGUI()

    def on_start(self):
        Clock.schedule_once(self.load_settings)

    def load_settings(self, dt):
        if self.store.exists('paths'):
            paths = self.store.get('paths')
            self.root.engine_path.text = paths.get('engine_path', '')
            self.root.nnue_path.text = paths.get('nnue_path', '')
            self.root.variant_path.text = paths.get('variant_path', '')

            # Auto-fill variant from NNUE path on startup
            self.root._update_variant_from_nnue(self.root.nnue_path, self.root.nnue_path.text)

    def on_stop(self):
        self.store.put('paths', 
                       engine_path=self.root.engine_path.text,
                       nnue_path=self.root.nnue_path.text,
                       variant_path=self.root.variant_path.text)


if __name__ == '__main__':
    ChessVariantPuzzlerApp().run()
