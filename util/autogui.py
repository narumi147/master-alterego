"""Image related processing"""
import io

import cv2
import imagehash as imagehash
import numpy
from PIL import ImageGrab, ImageFilter
from mss import mss
from scipy.signal import find_peaks
from skimage.feature import match_template as sk_match_template
from skimage.metrics import structural_similarity

from .dataset import *
from .gui import *
from .log import *

_screenshot_locker = threading.Lock()


# %% image processing
def get_mean_color(img: Image.Image, region: Sequence):
    if len(region) == 2:
        return img.getpixel(region)
    elif len(region) == 4:
        return numpy.mean(list(img.crop(region).getdata()), 0)
    else:
        raise KeyError(f'len(region) != 2 or 4. region={region}')


def cal_sim(img1: Image.Image, img2: Image.Image, region=None, method=None) -> float:
    """
    Calculate the similarity of two image at region.

    :param img1:
    :param img2:
    :param region: region to crop.
    :param method: 'template': cv2.matchTemplate, crop one slightly
                   'ssim': compute the mean structural similarity using `skimage`,
                   'hist': compute the similarity of color histogram,
                   'hash': image hash, value may be larger as expected.
    :return: similarity, float less than 1, may be negative.
    """
    if region is not None:
        img1 = img1.crop(region)
        img2 = img2.crop(region)
    if img1.width < img2.width:
        img2 = img2.resize((img1.width, img1.height))
    else:
        img1 = img1.resize((img2.width, img2.height))
    if img1.mode != 'RGB':
        img1 = img1.convert('RGB')
    if img2.mode != 'RGB':
        img2 = img2.convert('RGB')

    # if img1.width < 30:
    #     method = 'hist'
    if method is None:
        method = config.sim_algo or 'ssim'
    assert method in ('template', 'ssim', 'hist', 'hash'), method
    if method == 'template':
        dx = min(4, img2.width * 0.2)
        dy = min(4, img2.height * 0.2)
        img2 = img2.crop((dx, dy, img2.width - dx, img2.height - dy))
        sim = numpy.max(cv2.matchTemplate(pil_to_cv2(img1), pil_to_cv2(img2), cv2.TM_CCOEFF_NORMED))
        # print(f'sim={sim:.4f}')
        return sim
    elif method == 'ssim':
        try:
            # noinspection PyTypeChecker,PyUnusedLocal
            sim = structural_similarity(numpy.array(img1), numpy.array(img2), multichannel=True)
        except ValueError:
            """When cropped image size is too small(like <7), it will raise
            ValueError: win_size exceeds image extent.  If the input is a multichannel (color) image, 
            set multichannel=True."""
            logger.debug('skimage.metrics.structural_similarity failed. Use hist method instead.')
            sim = cal_sim(img1, img2, method='hist')
    elif method == 'hist':
        size = tuple(numpy.min((img1.size, img2.size), 0))
        if size != img1.size:
            img1 = img1.resize(size)
            img2 = img2.resize(size)
        lh = img1.histogram()
        rh = img2.histogram()
        # remove unused color where _l=_r=0
        diff = [1 - (0 if _l == _r else float(abs(_l - _r)) / max(_l, _r)) for _l, _r in zip(lh, rh) if _l + _r != 0]
        sim = sum(diff) / len(diff)
    elif method == 'hash':
        # https://stackoverflow.com/questions/843972/image-comparison-fast-algorithm
        img1 = img1.filter(ImageFilter.BoxBlur(radius=3))
        img2 = img2.filter(ImageFilter.BoxBlur(radius=3))
        phashvalue = imagehash.phash(img1) - imagehash.phash(img2)
        ahashvalue = imagehash.average_hash(img1) - imagehash.average_hash(img2)
        totalaccuracy = phashvalue + ahashvalue
        sim = 1 - totalaccuracy / 100
    else:
        raise ValueError(f'invalid method "{method}", only "ssim" and "hist" supported')
    # print(f'sim={sim:.4f}')
    return sim


def compress_image(image: Image.Image, scale=1, _format='jpeg', quality=-1, output: str = 'buffer'):
    """
    Compress image to io buffer(output='buffer') or a new Image object(output='pil').
    """
    output = output.lower()
    image1 = image.resize((int(image.width * scale), int(image.height * scale)))
    buffer = io.BytesIO()
    image1.save(buffer, _format, quality=quality)
    if output == 'buffer':
        return buffer
    else:
        image2: Image.Image = Image.open(buffer)
        return image2


# %% automatic
def _fix_length(images: Union[Image.Image, Sequence[Image.Image]], regions: Sequence):
    # fix to equal length of images and regions
    if isinstance(images, Image.Image):
        images = [images]
    # if images is None:
    #     images = [None]
    images = list(images)
    if regions is None:
        regions = [None] * len(images)
    elif isinstance(regions[0], (int, float)):
        regions = [regions] * len(images)
    else:
        if len(images) == len(regions):
            pass
        elif len(images) == 1:
            images = list(images) * len(regions)
        elif len(regions) == 1:
            regions = list(regions) * len(images)
        else:
            assert False, f'lengths should be equal or 1:\n {(images, regions)}'
    return images, regions


def screenshot(region: Sequence = None, filepath: str = None, monitor: int = None) -> Image.Image:
    """
    Take screenshot of multi-monitors.

    :param region: region inside monitor
    :param filepath: if not None, save to `filepath` then return Image
    :param monitor: 0-total size of all monitors, >0: monitor N, shown in system settings
    :return: PIL.Image.Image
    """
    with _screenshot_locker:
        if monitor is None:
            monitor = config.monitor
        _image = None
        size = (1920, 1080)  # default size
        if config.is_wda:
            try:
                _image = config.wda_client.screenshot().convert('RGB')
                size = _image.size
            except Exception as e:
                logger.error(f'Fail to grab screenshot WDA. Error:\n{e}')
        else:
            with mss() as sct:
                try:
                    mon = dict(sct.monitors[monitor])  # copy
                    # mon['width'], mon['height'] = size[0], size[1]  # introduce by dpi issue, force set screen size
                    shot = sct.grab(mon)
                    size = shot.size
                    # import pprint
                    # pprint.pprint(sct._monitors)
                    _image = Image.frombytes('RGB', size, shot.bgra, 'raw', 'BGRX').crop(region)
                except Exception as e:
                    logger.error(f'Fail to grab screenshot using mss(). Error:\n{e}')
                    if tuple(config.offset) == (0, 0):
                        # ImageGrab can only grab the main screen
                        try:
                            _image = ImageGrab.grab()
                        except Exception as e:
                            logger.error(f'Fail to grab screenshot using ImageGrad. Error:\n{e}')
        if _image is None:
            # grab failed, return an empty image with single color
            # wait for a moment for grabbing next screenshot
            _image = Image.new('RGB', size, (0, 255, 255)).crop(region)
            time.sleep(5)
        else:
            if filepath is not None:
                _image.save(filepath)
        return _image


def match_one_target(img: Image.Image, target: Image.Image, region: Sequence, threshold: float = None) -> bool:
    if threshold is None:
        threshold = THR
    return cal_sim(img, target, region) >= threshold


def match_targets(img, targets, regions=None, threshold=None, at=None, lapse=0.0):
    # type:(Image.Image,Union[Image.Image,Sequence[Image.Image]],Sequence,float,Union[int,Sequence],float)->bool
    """
    Match all targets. See `wait_targets`.
    `at` is a region or an **int** value of target index.

    :return: bool, matched or not.
    """
    if threshold is None:
        threshold = THR
    targets, regions = _fix_length(targets, regions)
    for target, region in zip(targets, regions):
        if cal_sim(img, target, region) < threshold:
            return False
    if at is None:
        pass
    elif isinstance(at, Sequence):
        click(at, lapse)
    elif at is not True and isinstance(at, int) and 0 <= at < len(regions):
        # add first condition since isinstance(True, int)=True
        click(regions[at], lapse)
    else:
        assert False, f'*at* should be int or a region: at={at}'
    return True


# 匹配第几个target
def match_which_target(img, targets, regions=None, threshold=None, at=None, lapse=0.0):
    # type:(Image.Image,Union[Image.Image,Sequence[Image.Image]],Sequence,float,Union[bool,Sequence],float)->int
    """
    Compare targets to find which matches. See `wait_which_target`.
    `at` is a region or **bool** value `True`, if True, click matched region.
    if target in `targets` is None, it will be skipped matching

    :return: matched index, return -1 if not matched.
    """
    if threshold is None:
        threshold = THR
    targets, regions = _fix_length(targets, regions)
    assert len(targets) > 1, f'length of targets or regions must be at least 2: {(len(targets), len(regions))}'
    res = -1
    for target, region in zip(targets, regions):
        res += 1
        if target is not None and cal_sim(img, target, region) >= threshold:
            if at is None:
                pass
            elif isinstance(at, Sequence):
                click(at, lapse)
            elif at is True:
                click(regions[res], lapse)
            else:
                assert False, f'*at* should be True or a region: at={at}'
            return res
    return -1


def wait_targets(targets, regions, threshold=None, at=None, lapse=0.0, clicking=None, interval=0.2):
    # type:(Union[Image.Image,Sequence[Image.Image]],Union[int,Sequence],float,Union[int,Sequence],float,Sequence,float)->None
    """
    Waiting screenshot to match all targets.

    :param : See `wait_which_target`
    :return: None
    """
    n = 0
    while True:
        n += 1
        if match_targets(screenshot(), targets, regions, threshold, at, lapse):
            return
        if clicking is not None:
            click(clicking, 0)
        sleep(interval)


# 直到匹配某一个target
def wait_which_target(targets, regions, threshold=None, at=None, lapse=0.0, clicking=None, interval=0.2):
    # type:(Union[Image.Image,Sequence[Image.Image]],Sequence,float,Union[bool,Sequence],float,Sequence,float)->int
    """
    Waiting for screenshot to match one of targets.

    :param targets: one Image or list of Image. Element of None will be skipped matching.
    :param regions: one region or list of region.
            `targets` or `regions` must contains at least 2 elements.
            length of targets and regions could be (1,n), (n,1), (n,n), where n>=2.
    :param threshold:
    :param at:  if True, click the region which target matches,
            if a region, click the region.
    :param lapse: lapse when click `at`.
    :param clicking: a region to click at until screenshot matches some target.
            e.g. Arash death animation, kizuna->rewards page.
    :param interval: interval of loop when no one matched.
    :return: the index which target matches.
    """
    while True:
        res = match_which_target(screenshot(), targets, regions, threshold, at, lapse)
        if res >= 0:
            return res
        if clicking is not None:
            for _ in range(3):
                click(clicking, 0)
        sleep(interval)


# 直到匹配模板
def wait_search_template(target: Image.Image, search_box=None, threshold: float = None, lapse=0.0, interval=0.2):
    """

    :param target: only target template, not full screenshot
    :param search_box: search box should be larger than target size
    :param threshold:
    :param lapse:
    :param interval:
    :return:
    """
    if threshold is None:
        threshold = THR
    while True:
        if search_target(screenshot(search_box), target)[0] >= threshold:
            time.sleep(lapse)
            return
        sleep(interval)


# 搜索目标模板存在匹配的最大值
# noinspection PyTypeChecker
def search_target(img: Image.Image, target: Image.Image, mode='cv2'):
    """
    find the max matched target in img.

    :param img:
    :param target:
    :param mode: 'cv2'(default) to use open-cv(quick), 'sk' to use skimage package(VERY slow)
            Attention: cv2 use (h,w), but PIL/numpy use (w,h).
    :return (max value, left-top pos)
    """
    # when scaling/relocate Regions, rect may have +-2 error range
    if img.width < target.width:
        target = target.crop((0, 0, img.width, target.height))
    if img.height < target.height:
        target = target.crop((0, 0, target.width, img.height))
    m1: numpy.ndarray = numpy.array(img.convert('RGB'))
    m2: numpy.ndarray = numpy.array(target.convert('RGB'))
    if mode == 'sk':
        matches: numpy.ndarray = sk_match_template(m1, m2)
        max_match = numpy.max(matches)
        pos = numpy.where(matches == max_match)
        return numpy.max(matches), (pos[1][0], pos[0][0])
    else:
        cv_img = cv2.cvtColor(m1, cv2.COLOR_RGB2BGR)
        cv_target = cv2.cvtColor(m2, cv2.COLOR_RGB2BGR)
        # h, w = cv_target.shape[0:2]
        matches = cv2.matchTemplate(cv_img, cv_target, cv2.TM_CCOEFF_NORMED)
        max_match = numpy.max(matches)
        pos = numpy.where(matches == max_match)
        # in PIL system, (x~w,y~h)
        return numpy.max(matches), (pos[1][0], pos[0][0])


# noinspection PyTypeChecker
def search_peaks(image: Image.Image, target: Image.Image, column=True, threshold: float = None,
                 **kwargs) -> numpy.ndarray:
    """
    Find target position in img which contains several targets. For simplicity, `target` and `image` should have
    the same width or height. Thus it's 1-D search.

    :param image:
    :param target:
    :param column: search target in column or in row direction.
    :param threshold:
    :param kwargs: extra args for `scipy.signal.find_peaks`
    :return: offsets of peaks in column/row direction.
    """
    if threshold is None:
        threshold = THR
    if column is True:
        assert image.size[0] == target.size[0], f'must be same width: img {image.size}, target {target.size}.'
    else:
        assert image.size[1] == target.size[1], f'must be same height: img {image.size}, target {target.size}.'
    m1: numpy.ndarray = numpy.array(image.convert('RGB'))
    m2: numpy.ndarray = numpy.array(target.convert('RGB'))
    cv_img, cv_target = (cv2.cvtColor(m1, cv2.COLOR_RGB2BGR), cv2.cvtColor(m2, cv2.COLOR_RGB2BGR))
    matches: numpy.ndarray = cv2.matchTemplate(cv_img, cv_target, cv2.TM_CCOEFF_NORMED)
    return find_peaks(matches.reshape(matches.size), height=threshold, **kwargs)[0]


def pil_to_cv2(img: Image.Image) -> numpy.ndarray:
    return cv2.cvtColor(numpy.array(img.convert('RGB')), cv2.COLOR_RGB2BGR)  # noqa


def cv2_to_pil(img: numpy.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
