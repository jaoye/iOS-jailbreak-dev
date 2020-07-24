"""
批量生成Assets格式的图片文件目录结构

共同特点:
1.图片组在'Assets.xcassets'目录下以每个图片组一个目录的结构存在
2.目录名以'.'为分割,前面的即为图片组在Xcode中显示名,后面代表了图片组的类型
3.图片组目录下存在至少一张图片 图片可能是png或者jpg但是在Xcode中不显示后缀名
4.图片组中的图片名可能包含@2x或者@3x的结尾,Xcode以此识别为不同分辨率屏幕对应的图片.
5.在应用中使用-[UIImage imageNamed:]方法使用图片时,传入参数imageName可以带后缀'png','jpg',也可以不带,都能够准确对应图片,但是不能带
    @2x或者@3x.
6.图片组目录中包含一个'Contents.json'的json文件,用于记录图片对应信息,基本格式:
    1)两个key:'images'和'info'
    2)'info'是固定结构,包含version=1和author="xcode"
    3)'images'为列表结构,区分图标图片和普通图片有不同结构

Appicon图片组特点:
1.目录以'.appiconset'结尾(Xcode默认为'AppIcon.appiconset')
2.'images'中每项都有:
    1)'size' 格式为"SSxSS" 其中'SS'为数字,代表了图片尺寸
    2)'idiom'可能为"iphone" "ipad" "ios-marketing"
    3)'filename'为目录下对应的图片文件名(包含后缀)
    4)'scale'代表缩放,可能为"1x","2x","3x"

普通图片组特点:
1.目录以'.imageset'结尾
2.'images'中每项:
    1)'idiom'代表对应设备,如果不区分iPad和iPhone固定为"universal"
    2)'scale'代表缩放  可能为"1x","2x","3x"
    3)'filename'为目录下对应的图片文件名(包含后缀) 如果没有对应缩放的图片则没有该key值

App包里的Assets.car里导出的图片必须先用pngcruch进行反处理
"""


import imghdr
import os
import sys
import json
import shutil
from copy import deepcopy

from PIL import Image


NEED_HANDLE_IMAGE_TYPES = ("png", "jpeg")
EMPTY_CONTENT_JSON = {"images": [], "info": {"version": 1, "author": "xcode"}}
APP_ICON_SET_INFO = (
    (20, 2, "iphone"),
    (20, 3, "iphone"),
    (29, 2, "iphone"),
    (29, 3, "iphone"),
    (40, 2, "iphone"),
    (40, 3, "iphone"),
    (60, 2, "iphone"),
    (60, 3, "iphone"),
    (20, 1, "ipad"),
    (20, 2, "ipad"),
    (29, 1, "ipad"),
    (29, 2, "ipad"),
    (40, 1, "ipad"),
    (40, 2, "ipad"),
    (50, 1, "ipad"),
    (50, 2, "ipad"),
    (72, 1, "ipad"),
    (72, 2, "ipad"),
    (76, 1, "ipad"),
    (76, 2, "ipad"),
    (83.5, 2, "ipad"),
    (1024, 1, "ios-marketing")
)


def need_to_handle(file_path):
    """
    判断是否为需要处理的图片格式
    :param file_path:文件路径
    :return:是否需要处理
    """
    image_type = imghdr.what(file_path)
    return image_type in NEED_HANDLE_IMAGE_TYPES


def get_executable_file_path_in_current_dir(name):
    """
    获取脚本所有目录下的可执行文件全路径
    :param name: 可执行文件名
    :return: 全路径
    """
    return os.path.join(sys.path[0], name)


def convert_optimized_pngs(file_path):
    """
    还原被Xcode处理过的png文件
    :param file_path: png文件路径
    :return:
    """
    dst_folder = os.path.split(file_path)[0]
    tmp_png_path = os.path.join(dst_folder, "temp.png")
    if not os.path.isdir(dst_folder):
        os.makedirs(dst_folder)
    pngcrush_file = get_executable_file_path_in_current_dir("pngcrush")
    cmd_options = ' -revert-iphone-optimizations -q '
    cammand_line = pngcrush_file + cmd_options + ' "'+file_path+'"  "'+tmp_png_path+'" \n'
    os.system(cammand_line)
    os.remove(file_path)
    os.rename(tmp_png_path, file_path)


def check_app_icon(source_image_path):
    """
    检查图标源文件是否符合要求
    :param source_image_path: 图标源文件
    :return: 检查结果
    """
    if not need_to_handle(source_image_path):
        print("图标必须是个图片!")
        return False
    img_w, img_h = Image.open(source_image_path).size
    if img_w != img_h:
        usr_input = input("图片长宽高不同,可能影响显示效果,仍要使用请输入'y'\n")
        return usr_input == 'y'
    if img_h < 1024:
        print("图片尺寸小于1024相素,可能影响显示效果,仍要使用请输入'y'\n")
        return False
    return True


def write_icon_info(size, scale, idiom, filename):
    """
    添加单个图标信息到图片组Contents.json
    :param size: 图标点尺寸
    :param scale: 缩放比例
    :param idiom: 对应
    :param filename: 对应的文件名
    :return:
    """
    try:
        info = json.load(open("Contents.json"))
    except FileNotFoundError:
        info = deepcopy(EMPTY_CONTENT_JSON)
    add_icon = {
        "size": "x".join((size, size)),
        "scale": scale,
        "idiom": idiom,
        "filename": filename
    }
    info["images"].append(add_icon)
    json.dump(info, open("Contents.json", "w"))


def clear_dir(icon_dir):
    """
    生成一个空的路径,如果已经存在,清空重新生成.
    :param icon_dir: 要生成的路径
    :return:
    """
    try:
        os.mkdir(icon_dir)
    except FileExistsError:
        shutil.rmtree(icon_dir)
        os.mkdir(icon_dir)


def process_app_icon_asset(source_image_path, dst_dir, icon_asset_name="AppIcon"):
    """
    生成AppIcon.appiconset图标
    :param source_image_path: 图标源文件
    :param dst_dir: 输出目录路径
    :param icon_asset_name: 图标组名,默认为"AppIcon"
    :return:
    """
    if not check_app_icon(source_image_path):
        return

    # 生成图片组
    os.chdir(dst_dir)
    icon_dir = ".".join((icon_asset_name, "appiconset"))
    clear_dir(icon_dir)
    os.chdir(icon_dir)
    for index, info in enumerate(APP_ICON_SET_INFO):
        size, scale, idiom = str(info[0]), str(info[1])+"x", info[2]
        image_name = icon_asset_name+size+idiom+"@"+scale+".png"
        # 生成图片
        im = Image.open(source_image_path)
        icon_size = info[0] * info[1]
        if im.size[0] != im.size[1]:
            im = im.resize((1024, 1024))
        im.thumbnail((icon_size, icon_size), Image.ANTIALIAS)
        im.save(image_name, 'png')
        # 保存对应信息
        write_icon_info(size, scale, idiom, image_name)
        print("成功添加图标", image_name)


def generate_assets_dir(dst_dir):
    """
    重新生成Assets.xcaassets包
    :param dst_dir: 保存包的路径,默认为桌面
    :return:生成包的路径
    """
    if not dst_dir:
        dst_dir = os.path.join(os.path.expanduser("~"), 'Desktop')
    assets_dir = os.path.join(dst_dir, "Assets.xcassets")
    clear_dir(assets_dir)
    return assets_dir


def get_image_set_info_by_file_name(file_name):
    """
    根据图片文件名获取图片组名
    :param file_name: 文件名
    :return: 图片组名, 缩放比例
    """
    # 获取去掉后缀的文件名
    strip_file_name = ".".join(file_name.split(".")[:-1])
    scale = 1
    image_set_name = strip_file_name
    if strip_file_name.endswith("@3x"):
        scale = 3
        image_set_name = strip_file_name.replace("@3x", "")
    elif strip_file_name.endswith("@2x"):
        scale = 2
        image_set_name = strip_file_name.replace("@2x", "")
    elif strip_file_name.endswith("@1x"):
        image_set_name = strip_file_name.replace("@1x", "")
    return image_set_name, scale


def add_single_image_to_assets(image_path, dst_dir):
    """
    添加单个图片文件到Assets
    :param image_path: 图片路径
    :param dst_dir: 输出路径
    :return:
    """
    image_file = os.path.basename(image_path)
    if image_file.lower().startswith("appicon") or "PackedAsset" in image_file:
        return
    image_set_name, scale = get_image_set_info_by_file_name(image_file)
    image_set_path = os.path.join(dst_dir, image_set_name+".imageset")
    json_path = os.path.join(image_set_path, "Contents.json")
    if not os.path.isdir(image_set_path):
        os.mkdir(image_set_path)
    try:
        info = json.load(open(json_path))
    except FileNotFoundError:
        info = deepcopy(EMPTY_CONTENT_JSON)
    images_info = info["images"]
    scale_info = str(scale)+"x"  # 转换成字符串的缩放信息
    single_image_info = {
        "idiom": "universal",  # TODO 这里以后可能根据设备进行区分,同时需要调整get_image_set_info_by_file_name方法
        "filename": image_file,
        "scale": scale_info
    }
    for exist_image_info in images_info:
        if exist_image_info.get("scale") == scale_info:
            print("已经存在", image_file, "将跳过该文件!")
            return
    images_info.append(single_image_info)
    added_img = os.path.join(image_set_path, image_file)
    shutil.copy(image_path, added_img)
    convert_optimized_pngs(added_img)
    json.dump(info, open(json_path, "w"))


def add_all_dir_images_to_assets(source_image_dir, dst_dir):
    """
    把一个路径下的所有图片添加到Assets(不包含子路径)
    :param source_image_dir: 要添加的图片文件夹路径
    :param dst_dir: 输出路径
    :return:
    """
    os.chdir(dst_dir)
    for item in os.listdir(source_image_dir):
        abs_path = os.path.join(source_image_dir, item)
        if os.path.isfile(abs_path) and need_to_handle(abs_path):
            add_single_image_to_assets(abs_path, dst_dir)
            print("正在添加图片", abs_path)


def process_obfuscation_images(images_dir):
    """
    优化图片,压缩大小,修改md5
    :param images_dir: 要处理的图片目录
    :return:
    """
    print("正在对所有图片进行优化处理,请等待....")
    img_obfuscation = get_executable_file_path_in_current_dir("imageObfuscation")
    cmd = "%s -s '%s' -t 90" % (img_obfuscation, images_dir)
    os.system(cmd)


def generate_image_assets():
    """
    生成Assets.car文件夹
    :return:
    """
    dst_dir = input("请输入要输出的文件夹,回车选择桌面\n").strip()
    assets_dir = generate_assets_dir(dst_dir)
    icon_file = input("请输入App图标文件,支持png和jpeg\n").strip()
    if icon_file:
        process_app_icon_asset(icon_file, assets_dir)
    source_image_dir = input("请输入要打包进Assets.car的图片文件夹,支持png和jpeg\n").strip()
    if source_image_dir:
        add_all_dir_images_to_assets(source_image_dir, assets_dir)
    process_obfuscation_images(assets_dir)
    print("图片添加完毕!")


if __name__ == "__main__":
    generate_image_assets()
