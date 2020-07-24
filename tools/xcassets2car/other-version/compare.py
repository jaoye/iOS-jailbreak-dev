import os
import random
import shutil
import string
import sys
import zipfile
from tkinter import Tk, Frame, Button, StringVar, Entry, Text, END, messagebox
import tkinter.filedialog

try:
    import magic
except ImportError:
    print('pip3 install python-magic-bin==0.4.14')
    sys.exit()
try:
    from macholib.MachO import MachO
except ImportError:
    print('pip3 install macholib==1.9')
    sys.exit()


class CompareApplication:
    def __init__(self):
        window = Tk()  # 创建一个窗口
        window.title("MachO compare")  # 设置标题
        center_window(window, 1200, 800)
        # window.maxsize(1200, 800)
        window.minsize(600, 400)

        frame1 = Frame(window)  # 创建一个框架
        frame1.pack(expand=False, fill='x')  # 将框架frame1放置在window中
        # window.grid(padx=20, pady=20)
        self.path1 = StringVar()
        self.path2 = StringVar()

        self.entry_path1 = Entry(frame1, width=120, textvariable=self.path1)
        bt_path1 = Button(frame1, text='选择原始 ipa 文件', command=self.pick_first)

        self.entry_path2 = Entry(frame1, width=120, textvariable=self.path2)
        bt_path2 = Button(frame1, text='选择混淆 ipa 文件', command=self.pick_second)
        self.entry_path1.insert(0, '/dev/shm/Fitfully.ipa')
        self.entry_path2.insert(0, '/dev/shm/Fitfully.1633_machine_code.1652.ipa')

        self.entry_path1.grid(row=0, column=0, padx=5, pady=5)
        bt_path1.grid(row=0, column=3, padx=5)
        self.entry_path2.grid(row=1, column=0, padx=5, pady=5)
        bt_path2.grid(row=1, column=3, padx=5)

        frame2 = Frame(window)  # 创建一个框架
        frame2.pack(expand=False, side='top', fill='x')  # 将框架frame2放置在window中
        start_btn = Button(frame2, text='START', command=self.start)
        start_btn.pack()

        # 创建格式化文本，并放置在window中
        self.text = Text(window)
        self.text.pack(expand=True, fill='both')
        self.text.insert(END, "Tip\n")
        self.text.insert(END, "1. 选择两个要比较的 ipa 文件, 或者粘贴路径\n")
        self.text.insert(END, "2. 点击 start\n")

        self.text.tag_config('warn', foreground='red')
        # 监测事件直到window被关闭
        window.mainloop()

    def pick_first(self):
        """
        获取第一个路径
        :return:
        """
        filename = tkinter.filedialog.askopenfilename()
        if filename:
            self.entry_path1.delete(0, END)
            self.entry_path1.insert(0, filename)
        else:
            self.entry_path1.delete(0, END)
            self.entry_path1.insert(0, "选择原始 ipa 文件")

    def pick_second(self):
        """
        获取第二个路径
        :return:
        """
        filename = tkinter.filedialog.askopenfilename()
        if filename:
            self.entry_path2.delete(0, END)
            self.entry_path2.insert(0, filename)
        else:
            self.entry_path2.delete(0, END)
            self.entry_path2.insert(0, "选择混淆 ipa 文件")

    def start(self):
        """
        开始解析,比较
        :return:
        """
        ipa_path1 = self.entry_path1.get()
        ipa_path2 = self.entry_path2.get()
        if not ipa_path1 or not ipa_path2:
            messagebox.showerror("Error", "先选择 ipa 文件")
            return
        if not os.path.isfile(ipa_path1):
            messagebox.showerror("Error", "原始 ipa 文件不正确")
            return
        if not os.path.isfile(ipa_path2):
            messagebox.showerror("Error", "混淆 ipa 文件不正确")
            return
        self.text.delete('1.0', END)
        path1 = decompression(ipa_path1)
        path2 = decompression(ipa_path2)

        try:
            main_path1, frameworks_list1 = find_main_and_framework(path1)
            main_path2, frameworks_list2 = find_main_and_framework(path2)
            print(main_path1, frameworks_list1)
            print(main_path2, frameworks_list2)
            if not main_path1:
                self.text.insert(END, "原 ipa 没有找到主儿进制")
                return
            if not main_path2:
                self.text.insert(END, "混淆 ipa 没有找到主儿进制")
                return

            self.text.insert(END, '主二进制 {}: \n'.format(os.path.basename(main_path1)))

            self.compare_machine_code(main_path1, main_path2)
            self.compare_text(main_path1, main_path2)
            for f_name in frameworks_list1:
                self.text.insert(END, '库二进制 {}: \n'.format(os.path.basename(f_name)))
                new_f_name = None
                for _name in frameworks_list2:
                    if _name.endswith(os.path.basename(f_name)):
                        new_f_name = _name
                        break
                self.compare_machine_code(f_name, new_f_name)
                self.compare_text(f_name, new_f_name)

        finally:
            shutil.rmtree(path1)
            shutil.rmtree(path2)

    def compare_machine_code(self, path1, path2):
        """
        比较机器码
        :param path1:
        :param path2:
        :return:
        """
        info1 = init_macho_info(path1)
        info2 = init_macho_info(path2)
        # print(info1)
        # print(info2)
        with open(path1, 'rb') as f1:
            f1.seek(info1.get('text_offset'))
            body1 = f1.read(info1.get('text_size'))
        with open(path2, 'rb') as f2:
            f2.seek(info2.get('text_offset'))
            body2 = f2.read(info2.get('text_size'))
        content = ''
        if len(body1) != len(body2):
            content += '__text段长度不同,混淆有问题'
            return
        step = 4
        arr1 = [body1[i:i + step] for i in range(0, len(body1), step)]
        arr2 = [body2[i:i + step] for i in range(0, len(body2), step)]
        self.text.insert(END, '    机器码:总指令数: {}\n'.format(len(arr1)))
        diff_counter = 0
        for index, point in enumerate(arr1):
            if point != arr2[index]:
                diff_counter += 1
        self.text.insert(END, '    机器码:变更的指令数: {}\n'.format(diff_counter))
        if diff_counter / len(arr1) < 0.1:
            self.text.insert(END, '    机器码:混淆百分比: {:.2%}\n'.format(diff_counter / len(arr1)), 'warn')
        else:
            self.text.insert(END, '    机器码:混淆百分比: {:.2%}\n'.format(diff_counter / len(arr1)))
        self.text.insert(END, '\n')
        # info2.get('text_offset')
        # info2.get('text_size')

    def compare_text(self, path1, path2):
        """
        比较 TEXT 段
        :param path1:
        :param path2:
        :return:
        """
        info1 = init_macho_info(path1)
        info2 = init_macho_info(path2)
        print(info1)
        with open(path1, 'rb') as f1:
            f1.seek(info1.get('class_offset'))
            class_body1 = f1.read(info1.get('class_size'))
            f1.seek(info1.get('cstring_offset'))
            cstring_body1 = f1.read(info1.get('cstring_size'))
            f1.seek(info1.get('methname_offset'))
            methname_body1 = f1.read(info1.get('methname_size'))
        with open(path2, 'rb') as f2:
            f2.seek(info2.get('class_offset'))
            class_body2 = f2.read(info2.get('class_size'))
            f2.seek(info2.get('cstring_offset'))
            cstring_body2 = f2.read(info2.get('cstring_size'))
            f2.seek(info2.get('methname_offset'))
            methname_body2 = f2.read(info2.get('methname_size'))

        self.compare_body(class_body1, class_body2, 'classname')
        self.compare_body(methname_body1, methname_body2, 'methname')
        self.compare_body(cstring_body1, cstring_body2, 'cstring')

    def compare_body(self, body1, body2, sub_type):
        """

        :param body1:
        :param body2:
        :param sub_type:
        :return:
        """
        arr1 = body1.split(b'\x00')
        arr2 = body2.split(b'\x00')
        total = len(arr1)
        counter = 0
        for index, class_name in enumerate(arr1):
            if class_name:
                if class_name != arr2[index]:
                    counter += 1
        self.text.insert(END, '    {}: 总数量: {}\n'.format(sub_type, total))
        self.text.insert(END, '    {}: 混淆的数量: {}\n'.format(sub_type, counter))
        if counter / total < 0.1:
            self.text.insert(END, '    {}: 百分比: {:.2%}\n'.format(sub_type, counter / total), 'warn')
        else:
            self.text.insert(END, '    {}: 百分比: {:.2%}\n'.format(sub_type, counter / total))

        self.text.insert(END, '\n')


def is_macho(file_path):
    """

    :param file_path:
    :return:
    """
    return magic.from_file(file_path, mime=True).find("x-mach-binary") > 0


def random_chars(length=8):
    """
    随机出 8位 字符串
    :return:
    """
    salt = ''.join(random.sample(string.ascii_letters + string.digits, length))
    return salt


def init_macho_info(macho_file):
    """

    :param macho_file:
    :return:
    """
    macho_obj = MachO(macho_file)
    for (_load_cmd, cmd, data) in macho_obj.headers[0].commands:
        try:
            segname = getattr(cmd, 'segname')
        except AttributeError:
            continue
        if segname.startswith(b'__TEXT'):
            params = dict()
            for _index, section in enumerate(data):
                sect_name = getattr(section, 'sectname')
                if sect_name.startswith(b'__text'):
                    text_offset = getattr(section, 'offset')
                    text_size = getattr(section, 'size')
                    params['text_offset'] = text_offset
                    params['text_size'] = text_size
                if sect_name.startswith(b'__objc_classname'):
                    class_offset = getattr(section, 'offset')
                    class_size = getattr(section, 'size')
                    params['class_offset'] = class_offset
                    params['class_size'] = class_size
                if sect_name.startswith(b'__objc_methname'):
                    methname_offset = getattr(section, 'offset')
                    methname_size = getattr(section, 'size')
                    params['methname_offset'] = methname_offset
                    params['methname_size'] = methname_size
                if sect_name.startswith(b'__cstring'):
                    cstring_offset = getattr(section, 'offset')
                    cstring_size = getattr(section, 'size')
                    params['cstring_offset'] = cstring_offset
                    params['cstring_size'] = cstring_size
                if sect_name.startswith(b'__objc_methtype'):
                    methtype_offset = getattr(section, 'offset')
                    methtype_size = getattr(section, 'size')
                    params['methtype_offset'] = methtype_offset
                    params['methtype_size'] = methtype_size
            return params
    return None


def namelist(path):
    dir_list = list()
    for _dir, _dirs, files in os.walk(path):
        for file in files:
            sub_file = os.path.join(_dir, file)
            dir_list.append(sub_file)
        for _d in _dirs:
            sub_file = os.path.join(_dir, _d)
            dir_list.append(sub_file)
    return dir_list


def find_main_and_framework(path):
    """

    :param path:
    :return:
    """
    main_path = None
    frameworks_home = None
    frameworks_list = list()
    file_list = namelist(path)
    for d in file_list:
        if os.path.isdir(d) and d.endswith('.app'):
            print(d)
            main_path = os.path.join(d, d.split('/')[-1].strip('.app'))
            print(main_path)
        if os.path.isdir(d) and d.endswith('.app/Frameworks'):
            frameworks_home = d
    if not main_path:
        return None, None
    listdir = os.listdir(frameworks_home)
    for _d in listdir:
        _path = os.path.join(frameworks_home, _d)
        if os.path.isdir(_path) and _d.endswith('framework'):
            f_name = _d.replace('.framework', '')
            frameworks_list.append(os.path.join(frameworks_home, _d, f_name))
    return main_path, frameworks_list


def decompression(ipa_file_path):
    """
    解压 ipa 文件
    并且将最低版本修改为 9
    :param ipa_file_path:
    :return:
    """
    chars = random_chars(10)
    tmp_dir = os.path.join('/tmp', chars)
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)

    # popen_command(['unzip', ipa_file_path, '-d', tmp_dir])
    ipa_file = zipfile.ZipFile(ipa_file_path, 'r')
    for file in ipa_file.namelist():
        try:
            if file.startswith('__MACOSX'):
                continue
            ipa_file.extract(file, tmp_dir)
        except UnicodeEncodeError:
            print(file)
    return tmp_dir


def center_window(root, width, height):
    screenwidth = root.winfo_screenwidth()
    screenheight = root.winfo_screenheight()
    size = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
    print(size)
    root.geometry(size)


CompareApplication()
