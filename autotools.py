# 2.3.7
import json,dataclasses,threading,subprocess,re,shutil,os,sys,time,webbrowser
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from collections import defaultdict
from tkinter import font


@dataclasses.dataclass
class Phone:
    SN: str
class Tools:
    """工具类，提供隐藏窗口的子进程执行方法"""
    @staticmethod
    def run_hidden(cmd, **kwargs):
        flags = {}
        if os.name == 'nt':
            flags['creationflags'] = subprocess.CREATE_NO_WINDOW
        kwargs.setdefault('shell', True)
        kwargs.setdefault('capture_output', True)
        kwargs.setdefault('text', True)
        return subprocess.run(cmd, **flags, **kwargs)  # 没有 timeout 参数

    @staticmethod
    def get_node(name):
        xml_file="config.xml"
        tree = ET.parse(xml_file)
        elem = tree.getroot().find(f'.//{name}')  # .// 表示任意层级
        return elem.text if elem is not None else None

    def extract_version(text):
        """提取版本号（数字和点）"""
        match = re.search(r'(\d+\.\d+\.\d+)', text)
        return match.group(1) if match else ""
class ConfigManager:
    """负责加载和创建配置文件"""
    def __init__(self, config_path='config.xml'):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        default_config = self._get_default_config()
        if not os.path.exists(self.config_path):
            print("config.xml 不存在，正在创建默认配置文件...")
            self._create_default_config(self.config_path, default_config)
            return default_config

        try:
            tree = ET.parse(self.config_path)
            root = tree.getroot()
            config = {}

            # 解析 window
            win = root.find('window')
            if win is not None:
                config['window'] = {
                    'title': win.findtext('title', default_config['window']['title']),
                    'width': int(win.findtext('width', default_config['window']['width'])),
                    'height': int(win.findtext('height', default_config['window']['height'])),
                    'x': int(win.findtext('x', default_config['window']['x'])),
                    'y': int(win.findtext('y', default_config['window']['y'])),
                    'alpha': float(win.findtext('alpha', default_config['window']['alpha'])),
                    'topmost': win.findtext('topmost', str(default_config['window']['topmost'])).lower() == 'true'
                }
            else:
                config['window'] = default_config['window']

            # 解析 oobe_tasks
            oobe = root.find('oobe_tasks')
            if oobe is not None:
                tasks = []
                for task in oobe.findall('task'):
                    desc = task.get('description', '')
                    cmd = task.text.strip() if task.text else ''
                    tasks.append((cmd, desc))
                config['oobe_tasks'] = tasks
            else:
                config['oobe_tasks'] = default_config['oobe_tasks']

            # 解析 precondition_tasks
            pre = root.find('precondition_tasks')
            if pre is not None:
                tasks = []
                for task in pre.findall('task'):
                    desc = task.get('description', '')
                    cmd = task.text.strip() if task.text else ''
                    tasks.append((cmd, desc))
                config['precondition_tasks'] = tasks
            else:
                config['precondition_tasks'] = default_config['precondition_tasks']

            # 解析 roll_commands
            roll = root.find('roll_commands')
            if roll is not None:
                cmds = []
                for cmd in roll.findall('command'):
                    name = cmd.get('name', '')
                    command = cmd.text.strip() if cmd.text else ''
                    cmds.append((name, command))
                config['roll_commands'] = cmds
            else:
                config['roll_commands'] = default_config['roll_commands']

            # 解析 settings
            settings = root.find('settings')
            if settings is not None:
                s = {}
                # pkgs
                pkgs_elem = settings.find('pkgs')
                if pkgs_elem is not None:
                    s['pkgs'] = [pkg.text.strip() for pkg in pkgs_elem.findall('pkg') if pkg.text]
                else:
                    s['pkgs'] = default_config['pkgs']

                # 日志容量选项
                log_opts_elem = settings.find('log_capacity_options')
                if log_opts_elem is not None:
                    s['log_capacity_options'] = [opt.get('value') for opt in log_opts_elem.findall('option') if
                                                  opt.get('value')]
                else:
                    s['log_capacity_options'] = default_config['settings']['log_capacity_options']

                # 日志容量命令映射
                cmd_map = {}
                for cmd_elem in settings.findall('log_capacity_command'):
                    size = cmd_elem.get('size')
                    cmd_text = cmd_elem.text.strip() if cmd_elem.text else ''
                    if size and cmd_text:
                        cmd_map[size] = cmd_text
                s['log_capacity_commands'] = cmd_map if cmd_map else default_config['settings']['log_capacity_commands']

                # 工作目录
                work_dir = settings.findtext('working_dir')
                s['working_dir'] = work_dir if work_dir else default_config['settings']['working_dir']

                # 线程数
                num_workers = settings.findtext('num_workers')
                s['num_workers'] = int(num_workers) if num_workers else default_config['settings']['num_workers']

                config['settings'] = s
            else:
                config['settings'] = default_config['settings']

            config['pkgs'] = config['settings'].get('pkgs', default_config['pkgs'])
            return config

        except Exception as e:
            print(f"解析 config.xml 失败: {e}，将使用默认配置并重新创建配置文件。")
            self._create_default_config(self.config_path, default_config)
            return default_config

    def _get_default_config(self):
        return {
            'window': {
                'title': '稳定性测试工具合集 v{version}',
                'width': 900,
                'height': 800,
                'x': 1000,
                'y': 200,
                'alpha': 0.95,
                'topmost': True
            },
            'oobe_tasks': [
                ("shell settings put secure user_setup_complete 1", "用户初始设置标志位"),
                ("shell settings put global device_provisioned 1", "设备初始配置标志位"),
                ("shell settings put system system_locales en-US", "设置语言和区域US"),
                ("shell setprop persist.sys.oobe_country other", "设置国家other"),
                ("reboot", "重启")
            ],
            'precondition_tasks': [
                ("shell settings put global development_settings_enabled 1", "设置开发者模式"),
                ("shell locksettings set-disabled true", "解除上划锁屏"),
                ("shell setprop persist.sys.timezone Asia/Shanghai", "设置时区亚洲/上海"),
                ("shell settings put system time_12_24 24", "设置24时制"),
                ("shell settings put global auto_time 0", "关闭自动设置时间"),
                ("shell date -s {now_str}", "设置系统时间"),
                ("shell settings put system screen_off_timeout 600000", "设置熄屏时长10min"),
                ("shell settings put global stay_on_while_plugged_in 7","充电不息屏"),
                ("shell audiotest_new setMasterMute1", "monkey 静音"),
                ("shell settings put system show_inadvertent %a%", "关闭防误触模式"),
                ("shell am start -n com.debug.loggerui/.MainActivity", "启动debuggerui"),
                ("{log_size_command}", "设置mobilelog容量"),
                ("shell am broadcast -a com.debug.loggerui.ADB_CMD -e cmd_name start --ei cmd_target 1 -n com.debug.loggerui/.framework.LogReceiver", "开启mobiellog"),
                ("shell am broadcast -a com.debug.loggerui.ADB_CMD -e cmd_name switch_taglog --ei cmd_target 1 -n com.debug.loggerui/.framework.LogReceiver", "启用Tag Log"),
                #高通开log
                ("shell setprop debug.logd.mainlogcat 1", "启用 main 缓冲区调试日志"),
                ("shell setprop debug.logd.systemlogcat 1", "启用 system 缓冲区调试日志"),
                ("shell setprop debug.logd.eventslogcat 1", "启用 events 缓冲区调试日志"),
                ("shell setprop debug.logd.radiologcat 1", "启用 radio 缓冲区调试日志"),
                ("shell setprop debug.logd.crashlogcat 1", "启用 crash 缓冲区调试日志"),
                ("shell setprop debug.logd.kernellogcat 1", "启用 kernel 缓冲区调试日志"),
                ("shell setprop debug.logd.securitylogcat 1", "启用 security 缓冲区调试日志")
            ],
            'roll_commands': [
                ("查看关键字报错",f"adb -s &lt;&gt; shell \"ls -l /data/aee_exp/; ls -l /data/vendor/aee_exp/\""),
                ("解除monkey静音","adb shell audiotest_new setMasterMute0"),
                ("进系统设置", "adb -s <> shell am start com.android.settings/.Settings\\$SystemDashboardActivity"),
                ("账号InfixID", "adb -s <> shell input text \"15696166898\""),
                ("账号InfixID密码", "adb -s <> shell input text \"@123456ota$\""),
                ("关机", "adb -s <>  reboot -p"),
                ("查看版本", "adb -s <> shell getprop ro.build.type"),
                ("测试", "adb -s <> shell echo check"),
                ("开发者模式并进入", "adb -s <> shell settings put global development_settings_enabled 1"),
                ("重启", "adb -s <> root"),
                ("关wifi", "adb -s <> shell \"svc wifi disable\""),
                ("连wifi:Stab-lab",
                 "adb -s <> shell \"svc wifi enable; cmd wifi start-scan; sleep 2; cmd wifi list-networks; cmd wifi connect-network \"Stab-lab\" wpa2 \"TransSi0n#2024\"\""),
                ("连wifi:OtaTest-lab",
                 "adb -s <> shell \"svc wifi enable; cmd wifi start-scan; sleep 2; cmd wifi list-networks; cmd wifi connect-network \"OtaTest-lab\" wpa2 \"OtaTest@123\"\""),
                ("连wifi:热点机",
                 "adb -s <> shell \"svc wifi enable; cmd wifi start-scan; sleep 2; cmd wifi list-networks; cmd wifi connect-network \"auto_test\" wpa2 \"12345678\"\""),
                ("输出账号", "adb -s <> shell input text \"jguo5575@gmail.com\""),
                ("输出密码", "adb -s <> shell input text \"gaokao2011\""),
                ("开发者选项界面", "adb -s <> shell am start -n com.android.settings/.DevelopmentSettings"),
                ("打开googlePlay",
                 "adb -s <> shell am start -n com.android.vending/com.google.android.finsky.activities.MainActivity")
            ],
            'pkgs': [
                "com.transsion.deskclock", "com.android.music",
                "com.android.calendar", "com.android.camera",
                "com.debug.loggerui", "com.android.settings"
            ],
            'settings': {
                'log_capacity_options': ['100G', '50G'],
                'log_capacity_commands': {
                    '100G': "shell am broadcast -a com.debug.loggerui.ADB_CMD -e cmd_name set_total_log_size_100000 --ei cmd_target 1 -n com.debug.loggerui/.framework.LogReceiver",
                    '50G': "shell am broadcast -a com.debug.loggerui.ADB_CMD -e cmd_name set_total_log_size_50000 --ei cmd_target 1 -n com.debug.loggerui/.framework.LogReceiver"
                },
                'working_dir': r"D:\tautoscriptproject",
                'num_workers': 10,
                'pkgs': [
                    "com.transsion.deskclock", "com.android.music",
                    "com.android.calendar", "com.android.camera",
                    "com.debug.loggerui", "com.android.settings"
                ],
                'black_list' : ["autotestX6877fff"]
            }
        }

    def _create_default_config(self, path, default_config):
        root = ET.Element("config")

        # window
        win = ET.SubElement(root, "window")
        ET.SubElement(win, "title").text = default_config['window']['title']
        ET.SubElement(win, "width").text = str(default_config['window']['width'])
        ET.SubElement(win, "height").text = str(default_config['window']['height'])
        ET.SubElement(win, "x").text = str(default_config['window']['x'])
        ET.SubElement(win, "y").text = str(default_config['window']['y'])
        ET.SubElement(win, "alpha").text = str(default_config['window']['alpha'])
        ET.SubElement(win, "topmost").text = str(default_config['window']['topmost']).lower()

        # oobe_tasks
        oobe = ET.SubElement(root, "oobe_tasks")
        for cmd, desc in default_config['oobe_tasks']:
            task = ET.SubElement(oobe, "task", description=desc)
            task.text = cmd

        # precondition_tasks
        pre = ET.SubElement(root, "precondition_tasks")
        for cmd, desc in default_config['precondition_tasks']:
            task = ET.SubElement(pre, "task", description=desc)
            task.text = cmd

        # roll_commands
        roll = ET.SubElement(root, "roll_commands")
        for name, cmd in default_config['roll_commands']:
            command_elem = ET.SubElement(roll, "command", name=name)
            command_elem.text = cmd

        # settings
        settings = ET.SubElement(root, "settings")
        pkgs_elem = ET.SubElement(settings, "pkgs")
        for pkg in default_config['pkgs']:
            ET.SubElement(pkgs_elem, "pkg").text = pkg

        log_opts = ET.SubElement(settings, "log_capacity_options")
        for opt in default_config['settings']['log_capacity_options']:
            ET.SubElement(log_opts, "option", value=opt)

        for size, cmd in default_config['settings']['log_capacity_commands'].items():
            cmd_elem = ET.SubElement(settings, "log_capacity_command", size=size)
            cmd_elem.text = cmd

        ET.SubElement(settings, "working_dir").text = default_config['settings']['working_dir']
        ET.SubElement(settings, "num_workers").text = str(default_config['settings']['num_workers'])

        try:
            ET.indent(root, space="  ")
        except AttributeError:
            pass

        tree = ET.ElementTree(root)
        tree.write(path, encoding="utf-8", xml_declaration=True)
        print(f"默认配置文件已创建: {path}")

    def get_config(self):
        return self.config
class DeviceManager:
    """管理设备列表和对应的进度条UI"""
    def __init__(self, parent_frame, progress_lock):
        self.parent_frame = parent_frame
        self.progress_lock = progress_lock
        self.devices_list = []
        self.device_order = []
        self.device_frames = {}
        self.device_progress_bars = {}
        self.device_progress_labels = {}
        self.device_status_labels = {}
        self.device_sn_labels = {}

        self._setup_ui()

    def _setup_ui(self):
        # 创建可滚动的Canvas用于容纳设备进度条
        self.canvas = tk.Canvas(self.parent_frame, bg="white", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.parent_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def bind_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def get_connect_devices(self):
        """获取当前连接的设备，并创建新设备的进度条"""
        result = Tools.run_hidden("adb devices", timeout=10)
        current_sns = []
        for line in result.stdout.splitlines():
            sn = line.split("\t")[0]

            black_list=["autotestX6877fff"]
            if sn in black_list:
                continue
            if "\tdevice" in line or "\tunauthorized" in line:
                current_sns.append(sn)
                if sn not in self.devices_list:
                    self.devices_list.append(sn)
                    self.create_device_progress_bar(sn)

        # 移除已断开的设备
        for sn in list(self.devices_list):
            if sn not in current_sns:
                self.devices_list.remove(sn)
                self.remove_device_progress_bar(sn)

        return self.devices_list

    def create_device_progress_bar(self, device_sn):
        if device_sn in self.device_frames:
            return
        self.device_order.insert(0, device_sn)
        device_frame = ttk.Frame(self.scrollable_frame, relief=tk.GROOVE, borderwidth=1, padding=5)
        if len(self.device_order) > 1:
            first_frame = self.device_frames[self.device_order[1]]
            device_frame.pack(fill=tk.X, pady=5, padx=5, before=first_frame)
        else:
            device_frame.pack(fill=tk.X, pady=5, padx=5)

        top_frame = ttk.Frame(device_frame)
        top_frame.pack(fill=tk.X, pady=(0, 5))

        sn_frame = ttk.Frame(top_frame)
        sn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        sn_label = ttk.Label(sn_frame, text=f"SN: {device_sn}", font=('Segoe UI', 9, 'bold'))
        sn_label.pack(anchor=tk.W)

        status_frame = ttk.Frame(top_frame)
        status_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))
        status_label = ttk.Label(status_frame, text="等待操作...", font=('Segoe UI', 8))
        status_label.pack(anchor=tk.CENTER)

        progress_frame = ttk.Frame(top_frame)
        progress_frame.pack(side=tk.RIGHT)
        progress_label = ttk.Label(progress_frame, text="0%", font=('Segoe UI', 9, 'bold'), width=6)
        progress_label.pack(anchor=tk.E)

        progress_bar = ttk.Progressbar(
            device_frame,
            orient=tk.HORIZONTAL,
            mode='determinate',
            style="Wide.Horizontal.TProgressbar",
            length=300
        )
        progress_bar.pack(fill=tk.X, pady=(0, 2))

        self.device_frames[device_sn] = device_frame
        self.device_progress_bars[device_sn] = progress_bar
        self.device_progress_labels[device_sn] = progress_label
        self.device_status_labels[device_sn] = status_label
        self.device_sn_labels[device_sn] = sn_label

    def update_device_progress(self, device_sn, value, maximum=None):
        if device_sn not in self.device_progress_bars:
            self.create_device_progress_bar(device_sn)
        progress_bar = self.device_progress_bars[device_sn]
        progress_label = self.device_progress_labels[device_sn]
        if maximum:
            progress_bar['maximum'] = maximum
        with self.progress_lock:
            progress_bar['value'] = value
            percentage = (value / progress_bar['maximum']) * 100 if progress_bar['maximum'] > 0 else 0
            progress_label['text'] = f"{percentage:.1f}%"

    def update_device_status(self, device_sn, status, color="black"):
        if device_sn not in self.device_status_labels:
            self.create_device_progress_bar(device_sn)
        status_label = self.device_status_labels[device_sn]
        status_label['text'] = status
        if color == "green":
            status_label['foreground'] = "green"
        elif color == "red":
            status_label['foreground'] = "red"
        else:
            status_label['foreground'] = "black"

    def remove_device_progress_bar(self, device_sn):
        if device_sn in self.device_frames:
            self.device_frames[device_sn].destroy()
            if device_sn in self.device_order:
                self.device_order.remove(device_sn)
            del self.device_frames[device_sn]
            del self.device_progress_bars[device_sn]
            del self.device_progress_labels[device_sn]
            del self.device_status_labels[device_sn]
            del self.device_sn_labels[device_sn]

    def clear_all(self):
        for device_sn in list(self.device_frames.keys()):
            self.remove_device_progress_bar(device_sn)
        self.device_order.clear()
class AutoHider:
    """窗口自动隐藏功能"""
    def __init__(self, root, alpha_var):
        self.root = root
        self.alpha_var = alpha_var
        self.is_hiding = False
        self.is_hidden = False
        self.is_showing = False
        self.checking_mouse = False
        self.auto_hide_enabled = True
        self.last_x = self.root.winfo_x()
        self.last_y = self.root.winfo_y()
        self.adsorb_threshold = 50
        self.has_focus = True
        self.mouse_in_window = True
        self.hidden_x = 0
        self.hidden_width = 900
        self.hidden_height = 600
        self.combo_timer_id = None
        self.radio_timer_id = None
        self.text_timer_id = None
        self._bind_events()

    def _bind_events(self):
        self.root.bind('<Configure>', self.on_window_move)
        self.root.bind('<FocusIn>', self.on_focus_in)
        self.root.bind('<FocusOut>', self.on_focus_out)
        self.root.bind('<Enter>', self.on_mouse_enter)
        self.root.bind('<Leave>', self.on_mouse_leave)

    def register_comboboxes(self, *combos):
        for combo in combos:
            combo.bind('<Button-1>', self.on_combo_click)
            combo.bind('<FocusIn>', self.on_combo_focus_in)
            combo.bind('<FocusOut>', self.on_combo_focus_out)

    def register_radiobuttons(self, *radios):
        for radio in radios:
            radio.bind('<Button-1>', self.on_radio_click)
            radio.bind('<FocusIn>', self.on_radio_focus_in)
            radio.bind('<FocusOut>', self.on_radio_focus_out)

    def register_text_area(self, text_area):
        text_area.bind('<Button-1>', self.on_text_click)
        text_area.bind('<FocusIn>', self.on_text_focus_in)
        text_area.bind('<FocusOut>', self.on_text_focus_out)

    def on_combo_click(self, event):
        self.auto_hide_enabled = False
        if self.combo_timer_id:
            self.root.after_cancel(self.combo_timer_id)
        self.combo_timer_id = self.root.after(2000, self.enable_auto_hide)

    def on_radio_click(self, event):
        self.auto_hide_enabled = False
        if self.radio_timer_id:
            self.root.after_cancel(self.radio_timer_id)
        self.radio_timer_id = self.root.after(2000, self.enable_auto_hide)

    def on_text_click(self, event):
        self.auto_hide_enabled = False
        if self.text_timer_id:
            self.root.after_cancel(self.text_timer_id)
        self.text_timer_id = self.root.after(2000, self.enable_auto_hide)

    def on_combo_focus_in(self, event):
        self.auto_hide_enabled = False

    def on_combo_focus_out(self, event):
        if self.combo_timer_id:
            self.root.after_cancel(self.combo_timer_id)
        self.combo_timer_id = self.root.after(1000, self.enable_auto_hide)

    def on_radio_focus_in(self, event):
        self.auto_hide_enabled = False

    def on_radio_focus_out(self, event):
        if self.radio_timer_id:
            self.root.after_cancel(self.radio_timer_id)
        self.radio_timer_id = self.root.after(1000, self.enable_auto_hide)

    def on_text_focus_in(self, event):
        self.auto_hide_enabled = False

    def on_text_focus_out(self, event):
        if self.text_timer_id:
            self.root.after_cancel(self.text_timer_id)
        self.text_timer_id = self.root.after(1000, self.enable_auto_hide)

    def enable_auto_hide(self):
        self.auto_hide_enabled = True
        self.check_should_hide()

    def on_window_move(self, event):
        if event.widget != self.root or self.is_hiding or self.is_showing:
            return
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if x == self.last_x and y == self.last_y:
            return
        self.last_x, self.last_y = x, y
        if not self.is_hidden and y < self.adsorb_threshold:
            self.root.geometry(f"{width}x{height}+{x}+0")
            self.last_x, self.last_y = x, 0
            self.hidden_x, self.hidden_width, self.hidden_height = x, width, height

    def on_focus_in(self, event):
        self.has_focus = True
        if self.is_hidden:
            self.start_show_animation()

    def on_focus_out(self, event):
        if not self.auto_hide_enabled:
            return
        self.has_focus = False
        self.check_should_hide()

    def on_mouse_enter(self, event):
        self.mouse_in_window = True
        if self.is_hidden:
            self.start_show_animation()
        self.root.after(10, lambda: self.root.focus_force())

    def on_mouse_leave(self, event):
        self.mouse_in_window = False
        self.check_should_hide()

    def check_should_hide(self):
        if (not self.auto_hide_enabled or self.is_hiding or
                self.is_showing or self.is_hidden):
            return
        y = self.root.winfo_y()
        if (y == 0 and not self.has_focus and not self.mouse_in_window and
                not self._checking_special_widgets()):
            self.start_hide_animation()

    def _checking_special_widgets(self):
        # 简化的检查，实际可更精细
        return False

    def start_hide_animation(self):
        if self.is_hiding or self.is_hidden:
            return
        self.is_hiding = True
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        target_y = 2 - height
        self.hidden_x, self.hidden_width, self.hidden_height = x, width, height
        threading.Thread(target=self._animate_hide, args=(x, y, target_y, width, height), daemon=True).start()

    def _animate_hide(self, start_x, start_y, target_y, width, height):
        frames = 15
        step = (target_y - start_y) / frames
        for i in range(frames + 1):
            if not self.is_hiding:
                return
            current_y = start_y + step * i
            self.root.after(0, lambda y=int(current_y): self.root.geometry(f"{width}x{height}+{start_x}+{y}"))
            time.sleep(0.02)
        self.is_hiding = False
        self.is_hidden = True
        self.root.attributes('-alpha', 0.01)
        self.root.attributes('-topmost', False)
        self._start_mouse_detection()

    def _start_mouse_detection(self):
        if not self.is_hidden or self.checking_mouse:
            return
        self.checking_mouse = True
        threading.Thread(target=self._check_mouse_near_hidden, daemon=True).start()

    def _check_mouse_near_hidden(self):
        delay = 0
        while self.is_hidden and self.checking_mouse:
            my = self.root.winfo_pointery()  # 鼠标的y坐标（屏幕坐标）
            if my <= 1:  # 鼠标在屏幕顶部边缘（y=0 或 y=1）
                delay += 1
                if delay >= 3:  # 停留约150ms后触发显示
                    self.root.after(0, self.start_show_animation)
                    break
            else:
                delay = 0
            time.sleep(0.05)
        self.checking_mouse = False

    def start_show_animation(self):
        if self.is_showing or not self.is_hidden:
            return
        self.is_hidden = False
        self.is_showing = True
        self.checking_mouse = False
        x = self.hidden_x
        width = self.hidden_width
        height = self.hidden_height
        start_y = 2 - height
        target_y = 0
        self.root.attributes('-alpha', self.alpha_var.get())
        threading.Thread(target=self._animate_show, args=(x, start_y, target_y, width, height), daemon=True).start()

    def _animate_show(self, start_x, start_y, target_y, width, height):
        frames = 15
        step = (target_y - start_y) / frames
        for i in range(frames + 1):
            if not self.is_showing:
                return
            current_y = start_y + step * i
            self.root.after(0, lambda y=int(current_y): self.root.geometry(f"{width}x{height}+{start_x}+{y}"))
            time.sleep(0.02)
        self.is_showing = False
        self.root.attributes('-topmost', False)
        self.root.after(50, self._after_show)

    def _after_show(self):
        self.root.focus_force()
        self.has_focus = True
        mx = self.root.winfo_pointerx()
        my = self.root.winfo_pointery()
        wx = self.root.winfo_x()
        wy = self.root.winfo_y()
        ww = self.root.winfo_width()
        wh = self.root.winfo_height()
        self.mouse_in_window = (wx <= mx <= wx + ww and wy <= my <= wy + wh)
        self.root.attributes('-alpha', self.alpha_var.get())
class TaskExecutor:
    """执行各种测试任务，每个设备只启动一次"""
    def __init__(self, config, device_manager, log_callback, warn_callback, pass_callback, log_size_combo):
        self.config = config
        self.device_manager = device_manager
        self.log = log_callback
        self.warn = warn_callback
        self.pass_log = pass_callback
        self.log_size_combo = log_size_combo  # 必须传入 Combobox 对象
        self.is_running = False
        self.now = datetime.now()
        self.oobe_task = config.get('oobe_tasks', [])
        self.predition_task = config.get('precondition_tasks', [])
        self.roll_command_list = config.get('roll_commands', [])
        self.pkgs = config.get('pkgs', [])
        self.working_dir = config.get('settings', {}).get('working_dir', '')

        # 每个任务类型的启动集合，防止重复启动
        self._oobe_started = set()
        self._predition_started = set()
        self._shutdown_started = set()
        self._oem_started = set()
        self._execute_started = set()
        self._userscene_started = set()

    def stop(self):
        """停止所有任务"""
        self.is_running = False

    def get_log_size_command(self, size):
        cmd_map = self.config.get('settings', {}).get('log_capacity_commands', {})
        if size in cmd_map:
            return cmd_map[size]
        self.warn(f"未找到容量 {size} 对应的命令，使用默认命令。")
        return "shell am broadcast -a com.debug.loggerui.ADB_CMD -e cmd_name set_total_log_size_100000 --ei cmd_target 1 -n com.debug.loggerui/.framework.LogReceiver"

    # ---------- OOBE ----------
    def start_oobe(self):
        self.device_manager.clear_all()
        self._oobe_started.clear()
        self.is_running = True
        threading.Thread(target=self._oobe_loop, daemon=True).start()

    def _oobe_loop(self):
        while self.is_running:
            devices = self.device_manager.get_connect_devices()
            for device in devices:
                if device not in self._oobe_started:
                    self._oobe_started.add(device)
                    self.device_manager.update_device_progress(device, 0, len(self.oobe_task))
                    self.device_manager.update_device_status(device, "开始OOBE操作")
                    threading.Thread(target=self._thread_oobe, args=(device,), daemon=True).start()
            time.sleep(1)

    def _thread_oobe(self, device):
        self.pass_log(f"正在执行 {device} OOBE操作")
        for i, (cmd, desc) in enumerate(self.oobe_task, 1):
            try:
                full_cmd = f"adb -s {device} {cmd}"
                self.device_manager.update_device_status(device, f"执行: {desc}")
                self.log(f"正在执行 {full_cmd} {desc}")
                Tools.run_hidden(full_cmd, check=True)
                self.device_manager.update_device_progress(device, i)
                self.device_manager.update_device_status(device, f"完成: {desc}", "green")
            except subprocess.CalledProcessError:
                self.device_manager.update_device_progress(device, i)
                if "reboot" not in cmd:
                    check_cmd = full_cmd.replace("set", "get").replace("1", "")
                    try:
                        out = Tools.run_hidden(check_cmd, check=True).stdout
                        if out not in [1, "EN", "en-US"]:
                            self.warn(f"执行 {device} {desc} 失败")
                            self.device_manager.update_device_status(device, f"失败: {desc}", "red")
                        else:
                            self.pass_log("done!")
                            self.device_manager.update_device_status(device, f"完成: {desc}", "green")
                    except:
                        self.warn(f"执行 {device} {desc} 失败")
                        self.device_manager.update_device_status(device, f"失败: {desc}", "red")
                else:
                    self.warn(f"执行 {device} {desc} 失败")
                    self.device_manager.update_device_status(device, f"失败: {desc}", "red")
            finally:
                self.pass_log("done!")
        self.device_manager.update_device_status(device, "OOBE操作完成", "green")
        self.pass_log(f"{device} 执行完毕")

    # ---------- 前置条件 ----------
    def start_predition(self):
        self.device_manager.clear_all()
        self._predition_started.clear()
        self.is_running = True
        threading.Thread(target=self._predition_loop, daemon=True).start()

    def _predition_loop(self):
        while self.is_running:
            devices = self.device_manager.get_connect_devices()
            for device in devices:
                if device not in self._predition_started:
                    self._predition_started.add(device)
                    self.device_manager.update_device_progress(device, 0, len(self.predition_task))
                    self.device_manager.update_device_status(device, "开始前置条件操作")
                    threading.Thread(target=self._thread_predition, args=(device,), daemon=True).start()
            time.sleep(1)

    def _thread_predition(self, device):
        self.pass_log(f"正在执行 {device} 前置操作")
        now_str = self.now.strftime('%m%d%H%M%Y.%S')
        log_size_cmd = self.get_log_size_command(self.log_size_combo.get())

        for i, (raw_cmd, desc) in enumerate(self.predition_task, 1):
            try:
                # 替换占位符
                cmd = raw_cmd.replace('{now_str}', now_str) \
                              .replace('{log_size_command}', log_size_cmd) \
                              .replace('{device}', device)
                full_cmd = f"adb -s {device} {cmd}"
                self.device_manager.update_device_status(device, f"执行: {desc}")
                self.log(f"正在执行 {full_cmd} {desc}")
                Tools.run_hidden(full_cmd, check=True)
                self.device_manager.update_device_progress(device, i)
                self.device_manager.update_device_status(device, f"完成: {desc}", "green")
            except Exception as e:
                self.device_manager.update_device_progress(device, i)
                self.device_manager.update_device_status(device, f"失败: {desc}", "red")
                self.warn(f"执行 {desc} 出错: {e}")
            finally:
                self.pass_log("done!")

        # 检查语言
        result = Tools.run_hidden(f"adb -s {device} shell getprop persist.sys.locale")
        if "en-US" not in result.stdout:
            self.log(f"发现 {device} 系统语言非English")
            Tools.run_hidden(f"adb -s {device} shell \"settings put system system_locales en-US\"")
            time.sleep(2)
            Tools.run_hidden(f"adb -s {device} shell \"stop && start\"")
            self.log("等待10秒重启服务")
            time.sleep(10)
            Tools.run_hidden(f"adb -s {device} shell \"setprop persist.sys.locale en-US\"")

        self.device_manager.update_device_status(device, "前置条件操作完成", "green")
        self.pass_log(f"{device} 执行完毕")

    # ---------- 批量关机 ----------
    def start_shutdown(self):
        self.device_manager.clear_all()
        self._shutdown_started.clear()
        self.is_running = True
        threading.Thread(target=self._shutdown_loop, daemon=True).start()

    def _shutdown_loop(self):
        while self.is_running:
            devices = self.device_manager.get_connect_devices()
            for device in devices:
                if device not in self._shutdown_started:
                    self._shutdown_started.add(device)
                    self.device_manager.update_device_progress(device, 0, len(self.pkgs) + 2)
                    self.device_manager.update_device_status(device, "开始批量关机")
                    threading.Thread(target=self._thread_shutdown, args=(device,), daemon=True).start()
            time.sleep(1)

    def _thread_shutdown(self, device):
        progress = 0
        self.pass_log("关闭Monkey进程")
        Tools.run_hidden(f"adb -s {device} shell \"pkill monkey\"")
        for pkg in self.pkgs:
            self.device_manager.update_device_status(device, f"结束进程: {pkg}")
            self.pass_log(f"{device} 正在结束进程: {pkg}")
            Tools.run_hidden(f"adb -s {device} shell am force-stop {pkg}", timeout=10)
            progress += 1
            self.device_manager.update_device_progress(device, progress)

        self.device_manager.update_device_status(device, "清理闹钟数据")
        Tools.run_hidden(f"adb -s {device} shell pm clear com.transsion.deskclock", check=True)
        progress += 1
        self.device_manager.update_device_progress(device, progress)

        self.device_manager.update_device_status(device, "正在关机")
        Tools.run_hidden(f"adb -s {device} reboot -p", check=True)
        progress += 1
        self.device_manager.update_device_progress(device, progress)
        self.device_manager.update_device_status(device, "关机完成", "green")

    # ---------- OEM解锁 ----------
    def start_oem_unlock(self):
        self.device_manager.clear_all()
        self._oem_started.clear()
        self.is_running = True
        threading.Thread(target=self._oem_loop, daemon=True).start()

    def _oem_loop(self):
        while self.is_running:
            devices = self.device_manager.get_connect_devices()
            for device in devices:
                if device not in self._oem_started:
                    self._oem_started.add(device)
                    self.device_manager.update_device_progress(device, 0, 1)
                    self.device_manager.update_device_status(device, "开始OEM解锁")
                    threading.Thread(target=self._thread_oem, args=(device,), daemon=True).start()
            time.sleep(1)

    def _thread_oem(self, device):
        self.pass_log(f"{device} 正在执行OEM解锁")

        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'wifi_config.json')
            cmd = rf'python -m pytest \\10.205.101.200\OTA_Version\05_个人备份\mulin.feng\tautoscriptproject\testcase\record\test_auto_OEM_unlock.py --sn={device} --config {config_path}'

            result = subprocess.run(
                cmd,
                shell=True,
                timeout=300,
                capture_output=True,
            )

            if result.returncode == 0:
                self.pass_log(f"{device}: 测试通过")
                self.device_manager.update_device_status(device, "OEM解锁成功", "green")
            else:
                self.warn(f"{device}: 测试失败 (代码: {result.returncode})")
                if result.stdout:
                    self.log(result.stdout)
                if result.stderr:
                    self.warn(result.stderr)
                self.device_manager.update_device_status(device, "OEM解锁失败", "red")

        except subprocess.TimeoutExpired as e:
            self.warn(f"{device}: 执行超时 - {e}")
            self.device_manager.update_device_status(device, f"超时: {e}", "red")
        except Exception as e:
            self.warn(f"{device}: 异常 - {e}")
            self.device_manager.update_device_status(device, f"异常: {e}", "red")
        finally:
            self.device_manager.update_device_progress(device, 1)

    # ---------- userscene前置 ----------
    def start_userscene_predition(self):
        self.device_manager.clear_all()
        self._userscene_started.clear()
        self.is_running = True
        threading.Thread(target=self._userscene_loop, daemon=True).start()

    def _userscene_loop(self):
        while self.is_running:
            devices = self.device_manager.get_connect_devices()
            for device in devices:
                if device not in self._userscene_started:
                    self._userscene_started.add(device)
                    self.device_manager.update_device_progress(device, 0, 1)
                    self.device_manager.update_device_status(device, "开始用户场景前置")
                    threading.Thread(target=self._thread_userscene, args=(device,), daemon=True).start()
            time.sleep(1)

    def _thread_userscene(self, device):
        self.pass_log(f"{device} 正在执行用户场景前置")
        try:
            cmd = rf'python -m pytest \\10.205.101.200\OTA_Version\05_个人备份\mulin.feng\tautoscriptproject\testcase\record\test_UserSenc_Predition.py --sn={device} --config {config_path}'
            self.log(f"执行命令: {cmd}")
            result = Tools.run_hidden(
                cmd,
                encoding='utf-8',
                timeout=300
            )

            # 输出详细日志
            if result.stdout:
                self.log(f"命令输出: {result.stdout}")
            if result.stderr:
                self.warn(f"命令错误: {result.stderr}")

            if result.returncode == 0:
                self.pass_log(f"{device}: 测试通过")
                self.device_manager.update_device_status(device, "用户场景前置设置成功", "green")
            else:
                self.warn(f"{device}: 测试失败 (代码: {result.returncode})")
                self.device_manager.update_device_status(device, "用户场景前置设置失败", "red")
        except Exception as e:
            self.warn(f"{device}: 异常 - {e}")
            import traceback
            self.warn(traceback.format_exc())
            self.device_manager.update_device_status(device, f"异常: {e}", "red")
        self.device_manager.update_device_progress(device, 1)

    # ---------- 批量执行代码 ----------
    def start_execute(self, selected_name):
        self.device_manager.clear_all()
        self._execute_started.clear()
        self.is_running = True
        threading.Thread(target=self._execute_loop, args=(selected_name,), daemon=True).start()

    def _execute_loop(self, selected_name):
        while self.is_running:
            devices = self.device_manager.get_connect_devices()
            for device in devices:
                if device not in self._execute_started:
                    self._execute_started.add(device)
                    self.device_manager.update_device_progress(device, 0, 1)
                    self.device_manager.update_device_status(device, "开始执行批量代码")
                    threading.Thread(target=self._thread_execute, args=(device, selected_name), daemon=True).start()
            time.sleep(1)

    def _thread_execute(self, device, selected_name):
        cmd_template = None
        for name, cmd in self.roll_command_list:
            if name == selected_name:
                cmd_template = cmd
                break
        if not cmd_template:
            self.warn(f"未找到命令: {selected_name}")
            self.device_manager.update_device_progress(device, 1)
            self.device_manager.update_device_status(device, "命令未找到", "red")
            return

        cmd = cmd_template.replace("<>", device).replace("{device}", device)
        self.device_manager.update_device_status(device, "正在执行命令")
        self.log(f"SN{device} 正在执行 {cmd}")
        try:
            result = Tools.run_hidden(cmd, check=True)
            self.pass_log(result.stdout)
            self.device_manager.update_device_progress(device, 1)
            self.device_manager.update_device_status(device, "执行成功", "green")
        except Exception as e:
            self.device_manager.update_device_status(device, "执行失败", "red")
            self.warn(f"执行出错: {e}")
            self.device_manager.update_device_progress(device, 1)
class Automation_testing_tool:
    """主窗口"""
    def __init__(self):
        # 加载配置
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
                # 窗口设置
        win_cfg = self.config.get('window', {})
        width = win_cfg.get('width', 900)
        height = win_cfg.get('height', 800)
        x = win_cfg.get('x', 1000)
        y = win_cfg.get('y', 200)
        alpha = win_cfg.get('alpha', 0.95)
        topmost = win_cfg.get('topmost', True)
        title = win_cfg.get('title', '稳定性测试工具合集 v{version}').replace('{version}', '2.3.7')

        # 创建主窗口
        self.root = tk.Tk()
        self.root.attributes('-topmost', topmost)
        self.alpha_value = tk.DoubleVar(value=alpha)
        self.root.title(title)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.configure(bg="#f0f0f0")
        self.root.attributes('-alpha', self.alpha_value.get())
        GradientScrollBanner(self.root)
        # 锁
        self.progress_lock = threading.Lock()

        # 创建UI框架
        self._create_ui()

        # 初始化组件
        self.device_manager = DeviceManager(self.device_progress_area, self.progress_lock)
        self.device_manager.bind_mousewheel()

        self.auto_hider = AutoHider(self.root, self.alpha_value)
        self.auto_hider.register_comboboxes(self.execute_combo, self.log_size_combo)
        self.auto_hider.register_radiobuttons(
            self.radio_oobe, self.radio_precondition, self.radio_shutdown,
            self.radio_execute, self.radio_oemunlock
        )
        self.auto_hider.register_text_area(self.text_area)

        self.task_executor = TaskExecutor(
            self.config,
            self.device_manager,
            self.update_log,
            self.warnning_log,
            self.pass_log,
            self.log_size_combo

        )

        # 初始化设备列表
        self.device_manager.get_connect_devices()
        self.device_count_label['text'] = f"就绪 | 检测到设备: {len(self.device_manager.devices_list)}"

    def _create_ui(self):
        # 样式
        self.style = ttk.Style()
        self.style.theme_use('vista')
        self.style.configure("Red.TButton", background="#e74c3c", foreground="red",
                             font=("Segoe UI", 10, "bold"), padding=6, borderwidth=1, relief="flat")
        self.style.configure("Green.TButton", background="#2ecc71", foreground="green",
                             font=("Segoe UI", 10, "bold"), padding=6, borderwidth=1, relief="flat")
        self.style.map("Red.TButton", background=[("active", "#c0392b")],
                       relief=[("pressed", "sunken"), ("!pressed", "flat")])
        self.style.map("Green.TButton", background=[("active", "#27ae60")],
                       relief=[("pressed", "sunken"), ("!pressed", "flat")])
        self.style.configure("Transparency.Horizontal.TScale", background="#f0f0f0", troughcolor="#e0e0e0")
        self.style.configure("TCombobox", fieldbackground="white", font=("Segoe UI", 9))
        self.style.configure("Wide.Horizontal.TProgressbar", background="#3498db", thickness=20, troughcolor="#ecf0f1")

        # 主框架
        self.main_frame = ttk.Frame(self.root, padding=15)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 控制面板
        self.control_frame = ttk.LabelFrame(self.main_frame, text="控制面板", padding=10)
        self.control_frame.pack(fill=tk.X, pady=(0, 10))

        # 透明度/置顶
        self.top_right_frame = ttk.Frame(self.control_frame)
        self.top_right_frame.pack(side=tk.RIGHT, padx=5, pady=5)

        self.transparency_frame = ttk.Frame(self.top_right_frame)
        self.transparency_frame.pack(fill=tk.X, pady=2)

        self.transparency_label_scale = ttk.Frame(self.transparency_frame)
        self.transparency_label_scale.pack(fill=tk.X)
        ttk.Label(self.transparency_label_scale, text="透明度:").pack(side=tk.LEFT, padx=(0, 5))
        self.alpha_scale = ttk.Scale(
            self.transparency_label_scale,
            from_=0.4, to=1.0,
            value=self.alpha_value.get(),
            orient=tk.HORIZONTAL,
            length=100,
            command=self.update_transparency,
            style="Transparency.Horizontal.TScale"
        )
        self.alpha_scale.pack(side=tk.LEFT)

        self.topmost_frame = ttk.Frame(self.transparency_frame)
        self.topmost_frame.pack(fill=tk.X, pady=(5, 0))
        self.topmost_var = tk.BooleanVar(value=self.config['window']['topmost'])
        self.topmost_check = ttk.Checkbutton(
            self.topmost_frame,
            text="置顶",
            variable=self.topmost_var,
            command=self.toggle_topmost
        )
        self.topmost_check.pack(side=tk.LEFT)

        # 左侧控制面板
        self.left_control_frame = ttk.Frame(self.control_frame)
        self.left_control_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Log容量
        log_frame = ttk.Frame(self.left_control_frame)
        log_frame.pack(fill=tk.X, pady=5)
        ttk.Label(log_frame, text="Log容量:       ").pack(side=tk.LEFT, padx=(0, 5))
        log_options = self.config.get('settings', {}).get('log_capacity_options', ['100G', '50G'])
        self.log_size = tk.StringVar(value=log_options[0])
        self.log_size_combo = ttk.Combobox(
            log_frame,
            textvariable=self.log_size,
            values=log_options,
            state="readonly",
            width=7
        )
        self.log_size_combo.pack(side=tk.LEFT)

        # 批量执行代码
        self.execute_frame = ttk.Frame(self.left_control_frame)
        self.execute_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.execute_frame, text="批量执行代码:").pack(side=tk.LEFT, padx=(0, 5))
        cmd_names = [item[0] for item in self.config.get('roll_commands', [])]
        self.execute_combo = ttk.Combobox(
            self.execute_frame,
            values=cmd_names,
            width=30,
            state="readonly"
        )
        self.execute_combo.set("这里选择批量执行的命令")
        self.execute_combo.bind("<<ComboboxSelected>>", lambda e: self.on_execute_selected())
        self.execute_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # 操作面板
        self.operation_frame = ttk.Frame(self.left_control_frame)
        self.operation_frame.pack(fill=tk.X, pady=10)

        self.button_start_or_stop = ttk.Button(
            self.operation_frame,
            text="▶",
            command=self.start_or_stop,
            style="Red.TButton",
            width=3
        )
        self.button_start_or_stop.pack(side=tk.LEFT, padx=(0, 15))

        self.operation_radio_option = tk.StringVar(value="")
        self.radio_oobe = ttk.Radiobutton(self.operation_frame, text='OOBE',
                                          command=self.switch_stop_button,
                                          variable=self.operation_radio_option, value="1")
        self.radio_oobe.pack(side=tk.LEFT, padx=5)
        self.radio_precondition = ttk.Radiobutton(self.operation_frame, text='前置条件',
                                                  command=self.switch_stop_button,
                                                  variable=self.operation_radio_option, value="2")
        self.radio_precondition.pack(side=tk.LEFT, padx=5)
        self.radio_shutdown = ttk.Radiobutton(self.operation_frame, text='批量关机',
                                              command=self.switch_stop_button,
                                              variable=self.operation_radio_option, value="3")
        self.radio_shutdown.pack(side=tk.LEFT, padx=5)
        self.radio_execute = ttk.Radiobutton(self.operation_frame, text='批量代码',
                                             command=self.switch_stop_button,
                                             variable=self.operation_radio_option, state="disabled", value="4")
        self.radio_execute.pack(side=tk.LEFT, padx=5)
        self.radio_oemunlock = ttk.Radiobutton(self.operation_frame, text="OEM解锁",
                                               command=self.switch_stop_button,
                                               variable=self.operation_radio_option, value="5")
        self.radio_oemunlock.pack(side=tk.LEFT, padx=5)
        self.radio_userscene = ttk.Radiobutton(self.operation_frame, text="用户场景前置",
                                               command=self.switch_stop_button,
                                               variable=self.operation_radio_option, value="6")
        self.radio_userscene.pack(side=tk.LEFT, padx=5)

        # 分割区域
        self.split_frame = ttk.Frame(self.main_frame)
        self.split_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 左侧设备进度区域（占2/5）
        self.device_progress_area = ttk.LabelFrame(self.split_frame, text="设备进度监控", padding=10)
        self.device_progress_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.device_progress_area.pack_propagate(False)
        self.device_progress_area.config(width=360)

        # 右侧日志区域（占3/5）
        self.log_area_frame = ttk.LabelFrame(self.split_frame, text="日志输出", padding=10)
        self.log_area_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.log_area_frame.pack_propagate(False)
        self.log_area_frame.config(width=540)

        self.text_area = tk.Text(
            self.log_area_frame,
            wrap="word",
            bg="white",
            fg="#333333",
            font=("Consolas", 9),
            insertbackground="#333333",
            selectbackground="#3498db",
            selectforeground="white"
        )
        self.text_area.tag_configure('red', foreground="red")
        self.text_area.tag_configure('green', foreground="green")
        self.scrollbar = ttk.Scrollbar(self.log_area_frame, orient='vertical', command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side='right', fill='y')
        self.text_area.pack(side='left', fill='both', expand=True)

        # 底部状态
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill=tk.X, pady=(5, 0))
        self.device_count_label = ttk.Label(
            self.status_frame,
            text="就绪 | 检测到设备: 0",
            foreground="#3498db",
            font=('Segoe UI', 9)
        )
        self.device_count_label.pack(side=tk.RIGHT, padx=5)

    # ---------- 主窗口回调 ----------
    def update_transparency(self, value):
        alpha = float(value)
        self.root.attributes('-alpha', alpha)
        self.alpha_value.set(alpha)

    def toggle_topmost(self):
        self.root.attributes('-topmost', self.topmost_var.get())

    def on_execute_selected(self):
        self.radio_execute.state(["!disabled"])
        self.radio_execute.invoke()
        self.pass_log("\n准备执行 " + self.execute_combo.get())

    def switch_stop_button(self):
        if self.task_executor.is_running:
            self.warnning_log("操作停止")
            self.task_executor.stop()
        self.button_start_or_stop.config(text="▶", style="Red.TButton")

    def start_or_stop(self):
        if self.button_start_or_stop["text"] == "▶":
            selected = self.operation_radio_option.get()
            if not selected:
                self.warnning_log("请先选择操作类型")
                return
            self.update_log("现在开始")
            self.button_start_or_stop.config(text="ІІ", style="Green.TButton")
            self.task_executor.is_running = True

            if selected == "1":
                self.pass_log("\n执行 OOBE 操作")
                self.task_executor.start_oobe()
            elif selected == "2":
                self.pass_log("\n执行 前置条件 操作")
                self.task_executor.start_predition()
            elif selected == "3":
                self.pass_log("\n执行 批量关机 操作")
                self.task_executor.start_shutdown()
            elif selected == "4":
                self.pass_log("\n执行 批量代码 操作")
                self.task_executor.start_execute(self.execute_combo.get())
            elif selected == "5":
                self.pass_log("\n执行 OEM解锁操作")
                self.task_executor.start_oem_unlock()
            elif selected == "6":
                self.pass_log("\n执行 用户场景前置操作")
                self.task_executor.start_userscene_predition()
        else:
            self.update_log("现在暂停")
            self.button_start_or_stop.config(text="▶", style="Red.TButton")
            self.task_executor.stop()

    def update_log(self, msg):
        self.text_area.insert(tk.END, str(msg) + "\n")
        self.text_area.see(tk.END)

    def warnning_log(self, msg):
        self.text_area.insert(tk.END, msg + "\n", "red")
        self.text_area.see(tk.END)
        self.text_area.update_idletasks()

    def pass_log(self, msg):
        self.text_area.insert(tk.END, msg + "\n", "green")
        self.text_area.see(tk.END)
        self.text_area.update_idletasks()

    def run(self):
        self.root.mainloop()
class GradientScrollBanner:
    def __init__(
            self,
            parent,
            start_color="#4f46e5",
            end_color="#06b6d4",
            speed=2
    ):
        text="🎉 欢迎使用稳定性工具合集🎉 未读取到公告内容，请确保前置工具进度完全走完"
        Notice_text_path = r"\\10.205.101.200\RelLOG1\mulin.feng\AutoTools\Notice.txt"
        try:
            with open(Notice_text_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except FileNotFoundError:
            print(f"文件不存在: {Notice_text_path}")
        except PermissionError:
            print("没有权限访问该文件")
        except Exception as e:
            print(f"错误: {e}")
        if not text:
            text="🎉 欢迎使用稳定性工具合集🎉"
        link_text = "点击查看工具手册"
        self.parent = parent
        self.speed = speed
        self.paused = False
        self.link_url = "https://transsioner.feishu.cn/wiki/N61FwEYZ9iZkX9km48tcuUrin9t"
        self.start_color = self.hex_to_rgb(start_color)
        self.end_color = self.hex_to_rgb(end_color)
        # 容器
        self.frame = tk.Frame(parent, bg=parent["bg"])
        self.frame.pack(fill=tk.X)

        # Canvas
        self.height = 28
        self.canvas = tk.Canvas(
            self.frame,
            height=self.height,
            bg=parent["bg"],
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.X)

        # 字体 & 文字
        self.font = font.Font(family="Microsoft YaHei UI", size=9)
        self.link_font = font.Font(family="Microsoft YaHei UI", size=9, underline=True)

        self.text_content = text + "　" * 1  # 普通公告文字
        self.link_content = link_text  # 链接文字

        self.text_id = self.canvas.create_text(
            0, self.height // 2,
            text=self.text_content,
            anchor=tk.W,
            fill="#ffffff",
            font=self.font
        )

        self.link_id = self.canvas.create_text(
            0, self.height // 2,
            text=self.link_content,
            anchor=tk.W,
            fill="#ffff00",  # 黄色，更显眼
            font=self.link_font,
            tags=("link",)  # 添加标签用于绑定事件
        )

        self.canvas.update_idletasks()
        text_bbox = self.canvas.bbox(self.text_id)
        link_bbox = self.canvas.bbox(self.link_id)
        self.text_width = (text_bbox[2] - text_bbox[0]) + (
                link_bbox[2] - link_bbox[0]) if text_bbox and link_bbox else 200
        self.canvas_width = self.canvas.winfo_width()
        self.scroll_position = 0

        # 渐变背景（PIL）
        self.gradient_img = None
        self.gradient_item = None
        self.draw_gradient()

        # 事件
        self.canvas.tag_bind("link", "<Button-1>", self.open_link)
        self.canvas.tag_bind("link", "<Enter>", self.on_link_enter)
        self.canvas.tag_bind("link", "<Leave>", self.on_link_leave)
        self.canvas.bind("<Enter>", lambda e: setattr(self, 'paused', True))
        self.canvas.bind("<Leave>", lambda e: setattr(self, 'paused', False))
        self.canvas.bind("<Configure>", self.on_resize)

        self.scroll()

    # 渐变（PIL 生成一次，Canvas 复用）
    def draw_gradient(self):
        from PIL import Image, ImageTk
        width = max(self.canvas_width, 1)
        height = self.height

        image = Image.new("RGB", (width, height))
        pixels = image.load()

        for x in range(width):
            ratio = x / width
            r = int(self.start_color[0] * (1 - ratio) +
                    self.end_color[0] * ratio)
            g = int(self.start_color[1] * (1 - ratio) +
                    self.end_color[1] * ratio)
            b = int(self.start_color[2] * (1 - ratio) +
                    self.end_color[2] * ratio)

            for y in range(height):
                pixels[x, y] = (r, g, b)

        self.gradient_img = ImageTk.PhotoImage(image)

        if self.gradient_item is None:
            self.gradient_item = self.canvas.create_image(
                0, 0,
                anchor=tk.NW,
                image=self.gradient_img
            )
            self.canvas.tag_lower(self.gradient_item)
        else:
            self.canvas.itemconfig(self.gradient_item, image=self.gradient_img)

    # 滚动

    def scroll(self):
        if not self.paused:
            self.scroll_position -= self.speed

            if self.scroll_position <= -self.text_width:
                self.scroll_position = self.canvas_width

            self.canvas.coords(
                self.text_id,
                self.scroll_position,
                self.height // 2
            )

            text_bbox = self.canvas.bbox(self.text_id)
            if text_bbox:
                link_x = text_bbox[2] + 5  # 普通文字右侧 + 5像素间距
                self.canvas.coords(
                    self.link_id,
                    link_x,
                    self.height // 2
                )

        self.frame.after(16, self.scroll)
    def open_link(self, event):
        webbrowser.open(self.link_url)
        print(f"打开链接: {self.link_url}")

    def on_link_enter(self, event):
        self.canvas.config(cursor="hand2")

    def on_link_leave(self, event):
        self.canvas.config(cursor="")


    # Resize（节流 + 单图重绘）

    def on_resize(self, event):
        if hasattr(self, "_after_id"):
            self.frame.after_cancel(self._after_id)

        self._after_id = self.frame.after(
            80,
            lambda: self._real_resize(event.width)
        )

    def _real_resize(self, width):
        self.canvas_width = width
        self.draw_gradient()

    # 工具

    @staticmethod
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))



def get_version_from_filename(filename):
    match = re.search(r'V(\d+(?:\.\d+)+)', filename, re.IGNORECASE)
    return match.group(0).upper() if match else None

def compare_versions(ver1, ver2):
    if not ver1 or not ver2:
        return 0
    v1 = ver1[1:] if ver1[0].upper() == 'V' else ver1
    v2 = ver2[1:] if ver2[0].upper() == 'V' else ver2
    v1_parts = list(map(int, v1.split('.')))
    v2_parts = list(map(int, v2.split('.')))
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts += [0] * (max_len - len(v1_parts))
    v2_parts += [0] * (max_len - len(v2_parts))
    for i in range(max_len):
        if v1_parts[i] > v2_parts[i]:
            return 1
        elif v1_parts[i] < v2_parts[i]:
            return -1
    return 0

def rename_current_file(old_path, new_version):
    dir_path = os.path.dirname(old_path)
    old_filename = os.path.basename(old_path)
    base_name = re.sub(r'\s*V\d+(?:\.\d+)*\s*', '', old_filename.replace('.py', '')).strip()
    new_filename = f"{base_name} {new_version}.py"
    new_path = os.path.join(dir_path, new_filename)
    shutil.move(old_path, new_path)
    return new_path

def mode_update(resouse):
    """检查并更新依赖包"""
    print("开始检查依赖包...")

    # 1. 检查并安装 Pillow
    try:
        pillow_result = subprocess.run(
            "python -m pip show pillow",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        pillow_version = pillow_result.stdout if pillow_result.stdout else ""

        if "Version" not in pillow_version:
            print("⚠️ Pillow未安装，正在安装...")
            subprocess.run(
                f"python -m pip install pillow {resouse} --default-timeout=100",
                shell=True,
                check=True
            )
            print("✓ Pillow安装完成")
        else:
            # 提取版本号
            for line in pillow_version.splitlines():
                if line.startswith("Version:"):
                    print(f"✓ Pillow已安装，版本: {line.split(':')[1].strip()}")
                    break
    except subprocess.TimeoutExpired:
        print("⚠️ 检查Pillow超时")
    except Exception as e:
        print(f"⚠️ 检查Pillow出错: {e}")

    # 2. 检查并安装 pytest
    try:
        pytest_result = subprocess.run(
            "python -m pytest --version",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        pytest_version = pytest_result.stdout if pytest_result.stdout else ""

        if not pytest_version or "not found" in pytest_version.lower() or "NO" in pytest_version:
            print("⚠️ pytest未安装，正在安装...")
            subprocess.run(
                f"python -m pip install pytest {resouse} --default-timeout=100",
                shell=True,
                check=True
            )
            print("✓ pytest安装完成")
        else:
            # 提取版本号
            version_match = re.search(r'(\d+\.\d+\.\d+)', pytest_version)
            if version_match:
                print(f"✓ pytest已安装，版本: {version_match.group(1)}")
            else:
                print("✓ pytest已安装")
    except subprocess.TimeoutExpired:
        print("⚠️ 检查pytest超时")
    except Exception as e:
        print(f"⚠️ 检查pytest出错: {e}")

    # 3. 检查并更新 tcorecapalib
    try:
        # 检查当前安装的版本
        installed_result = subprocess.run(
            "python -m pip index versions tcorecapalib --index-url https://artifact.transsion.com/artifactory/api/pypi/AT-TCoreLib/simple | findstr INSTALLED",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        tcorecapalib_version = Tools.extract_version(installed_result.stdout) if installed_result.stdout else ""

        # 检查最新版本
        latest_result = subprocess.run(
            "python -m pip index versions tcorecapalib --index-url https://artifact.transsion.com/artifactory/api/pypi/AT-TCoreLib/simple | findstr LATEST",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        tcorecapalib_version_by_network = Tools.extract_version(latest_result.stdout) if latest_result.stdout else ""

        # 判断是否需要安装或更新
        if not tcorecapalib_version:
            print("⚠️ tcorecapalib未安装，正在安装...")
            subprocess.run(
                "python -m pip install tcorecapalib "
                "-i https://artifact.transsion.com/artifactory/api/pypi/AT-TCoreLib/simple "
                "--extra-index-url https://pypi.org/simple "
                "--trusted-host artifact.transsion.com",
                shell=True,
                check=True
            )
            print("✓ tcorecapalib安装完成")
        elif tcorecapalib_version_by_network and tcorecapalib_version != tcorecapalib_version_by_network:
            print(f"⚠️ 发现新版本 tcorecapalib {tcorecapalib_version_by_network}，当前版本 {tcorecapalib_version}")
            print("正在更新...")
            subprocess.run("chcp 65001", shell=True)  # 设置控制台编码
            subprocess.run(
                "python -m pip install tcorecapalib --upgrade "
                "-i https://artifact.transsion.com/artifactory/api/pypi/AT-TCoreLib/simple "
                "--extra-index-url https://pypi.org/simple "
                "--trusted-host artifact.transsion.com",
                shell=True,
                check=True
            )
            print(f"✓ tcorecapalib已更新到版本 {tcorecapalib_version_by_network}")
        else:
            print(f"✓ tcorecapalib已是最新版本: {tcorecapalib_version}")
    except subprocess.TimeoutExpired:
        print("⚠️ 检查tcorecapalib超时")
    except Exception as e:
        print(f"⚠️ 检查tcorecapalib出错: {e}")

    print("依赖检查完成")

if __name__ == "__main__":
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'wifi_config.json')
    print("查找配置文件")
    # 判断 wifi_config.json 是否存在，不存在则创建
    if not os.path.exists(config_path):
        config_data = {
            "wifi": "auto_test",
            "wifi_password": "00000000",
            "google_id": "hgou62415@gmail.com",
            "google_password": "gouhuang1019@",
            "google_infinix_password": "liuxia.Test@1229"
}
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        print(f"已创建配置文件: {config_path}")
    else:
        print(f"配置文件已存在: {config_path}")
    current_version = "V2.3.7"  # 更新为当前版本
    current_file = __file__
    current_filename = os.path.basename(current_file)
    actual_version = get_version_from_filename(current_filename)
    if not actual_version:
        actual_version = current_version
    target_dir = rf"\\10.205.101.200\RelLOG1\mulin.feng\AutoTools"
    latest_file = None
    latest_version = None
    latest_filename = None
    try:
        if os.path.exists(target_dir):
            for filename in os.listdir(target_dir):
                if filename.startswith("Automation_testing_tool") and filename.endswith(".py"):
                    file_version = get_version_from_filename(filename)
                    if file_version:
                        if latest_version is None or compare_versions(file_version, latest_version) > 0:
                            latest_version = file_version
                            latest_file = os.path.join(target_dir, filename)
                            latest_filename = filename
    except Exception:
        latest_file = None
    if latest_file and compare_versions(actual_version, latest_version) < 0:
        print(f"检测到新版本 {latest_version}，正在更新...")
        try:
            shutil.copy2(latest_file, current_file)
            new_file_path = rename_current_file(current_file, latest_version)
            print(f"已更新到版本 {latest_version}")
            print(f"文件名已更新为: {os.path.basename(new_file_path)}")
            os.execv(sys.executable, ['python', new_file_path] + sys.argv[1:])
        except Exception as e:
            print(f"更新失败: {e}")

    try:
        mode_update('-i https://pypi.tuna.tsinghua.edu.cn/simple')
    except Exception as e:
        print(e)
        print("依赖安装失败，尝试换源")
        try:mode_update(' ')
        except Exception as e:
            print(e)
            print("安装失败，请检查网络是否连通")
    app = Automation_testing_tool()
    app.run()