import os
import threading
import traceback
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

import generator
import puzzler
import pgn

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

    def _log_message(self, text):
        message = text if text.endswith('\n') else text + '\n'
        self.append_output(message.strip())
        try:
            with open('app.log', 'a', encoding='utf8') as log_file:
                log_file.write(message)
        except OSError:
            pass

    def _build_uci_options(self):
        options = {}
        if self.threads.text.strip():
            options['Threads'] = self.threads.text.strip()
        if self.hash_size.text.strip():
            options['Hash'] = self.hash_size.text.strip()
        if self.nnue_path.text.strip():
            options['EvalFile'] = self.nnue_path.text.strip()
        if self.variant_path.text.strip():
            options['VariantPath'] = self.variant_path.text.strip()
        return options

    def _make_progress_callback(self, progress_bar, fallback_total=None):
        def _callback(done, total):
            total = total or fallback_total
            if total and total > 0:
                percent = int((done / total) * 100)
            else:
                percent = min(progress_bar.value + 1, 100)
            self.update_progress(progress_bar, max(0, min(percent, 100)))
        return _callback

    def _handle_failure(self, context, exc):
        stack = traceback.format_exc()
        self._log_message(f"✗ {context}: {exc}")
        self.append_output(stack)
        try:
            with open('app.log', 'a', encoding='utf8') as log_file:
                log_file.write(stack + '\n')
        except OSError:
            pass

    def _count_puzzles_in_file(self, path):
        try:
            with open(path, 'r', encoding='utf8') as f:
                return sum(1 for line in f if line.strip())
        except OSError as exc:
            self._log_message(f"Unable to count puzzles in {path}: {exc}")
            return 0

    def _convert_to_pgn(self, epd_path):
        pgn_path = epd_path[:-4] + '.pgn' if epd_path.endswith('.epd') else epd_path + '.pgn'
        try:
            self._log_message(f"Converting {epd_path} to {pgn_path}...")
            pgn.sf.set_option("VariantPath", self.variant_path.text.strip())
            with open(epd_path, 'r', encoding='utf8') as epd_stream, open(pgn_path, 'w', encoding='utf8') as pgn_stream:
                pgn.epd_to_pgn(epd_stream, pgn_stream)
            self._log_message(f"✓ Converted to {pgn_path}")
        except Exception as exc:
            self._handle_failure('PGN conversion failed', exc)

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

    def _workflow_thread(self):
        try:
            engine_path = self.engine_path.text.strip()
            variant = self.variant.text.strip() or 'chess'
            gen_output_path = self.input_file.text.strip() or 'positions.epd'
            puzzler_output_path = self.output_file.text.strip() or 'puzzles.epd'

            if not engine_path:
                self._log_message('Please specify the engine path before running.')
                return

            try:
                count = int(self.num_games.text.strip())
                depth = int(self.depth.text.strip())
            except ValueError:
                self._log_message('Count and depth must be integers.')
                return

            if count <= 0 or depth <= 0:
                self._log_message('Count and depth must be positive values.')
                return

            uci_options = self._build_uci_options()

            self._log_message('Generating candidate positions...')
            generator.run_generator(
                engine_path,
                variant,
                count,
                gen_output_path,
                ucioptions=uci_options,
                progress_callback=self._make_progress_callback(self.generator_progress, count)
            )
            self.update_progress(self.generator_progress, 100)
            self._log_message(f'✓ Positions generated to {gen_output_path}')

            self._log_message('Extracting puzzles...')
            puzzler.run_puzzler(
                engine_path,
                gen_output_path,
                puzzler_output_path,
                variant=variant,
                depth=depth,
                ucioptions=uci_options,
                progress_callback=self._make_progress_callback(self.puzzler_progress)
            )
            self.update_progress(self.puzzler_progress, 100)
            self._log_message(f'✓ Puzzles extracted to {puzzler_output_path}')

            num_puzzles = self._count_puzzles_in_file(puzzler_output_path)
            self.update_puzzle_count(num_puzzles)

            if self.pgn_checkbox.active:
                self._convert_to_pgn(puzzler_output_path)
        except Exception as exc:
            self._handle_failure('Workflow failed', exc)
        finally:
            Clock.schedule_once(lambda dt: setattr(self.run_button, 'disabled', False), 0)


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
