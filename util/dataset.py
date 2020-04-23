"""Data definition, constants
Coordination: using PIL coordination, (x,y), (left,top,right,bottom), e.g. (0,0,1920-1,1080-1)
"""

from PIL import Image

from .base import *

THR = 0.85  # default threshold


class _Regions:
    """
    Base class to store region(length 4) or point(length 2) data at default screen size 1920*1080.
    Attributes(except width and height are int value) must be the assembly of point and region.
    """
    width = 1920
    height = 1080
    box = (0, 0, width, height)

    # for those regions differ in cn and jp version, use two private vars and getter
    # don't use double underline "__" as prefix for attribute name, otherwise it will be ignored.
    _test_cn = (0, 0, 100, 100)
    _test_jp = (0, 0, 90, 90)

    @property
    def test(self):
        return self._test_jp if config.is_jp else self._test_cn

    @staticmethod
    def relocate_one(region, new: Sequence, old: Sequence = (0, 0, 1919, 1079)):
        assert isinstance(region, Sequence), f'region should be Sequence: {region}'
        if not region:  # empty
            return region
        elif isinstance(region[0], Sequence):
            return tuple([Regions.relocate_one(r, new, old) for r in region])
        elif isinstance(region[0], (int, float)):
            length = len(region)
            assert length % 2 == 0, f'region length must be 2(point) or 4(rect): {region}'
            if length > 4:
                print(f'warning: more than 4 elements: {region}')
            out = []
            for i in range(length // 2):
                x, y = region[i * 2:i * 2 + 2]
                x2 = (x - old[0]) / (old[2] - old[0]) * (new[2] - new[0]) + new[0]
                y2 = (y - old[1]) / (old[3] - old[1]) * (new[3] - new[1]) + new[1]
                # (x,y) coordinates: in PIL it will be round then int.
                out.append(int(round(x2)))
                out.append(int(round(y2)))
            return tuple(out)
        else:
            raise ValueError(f'elements must be numbers: {region}')

    def relocate(self, box: Sequence):
        """
        Recursively resize regions of original class attributes not `self`.

        :param box: new region located in screenshot, (x0,y0,x1,y1): 0 <= x0 < x1 < width, 0 <= y0 < y1 < height.
                     old box always use `self.__class__.box`
        """
        assert len(box) == 4, f'box must be length 4: {box}'
        self.width = int(box[2] - box[0])
        self.height = int(box[3] - box[1])
        for key in dir(self.__class__):
            attr = getattr(self.__class__, key)
            if not key.startswith('__') and isinstance(attr, Sequence):
                setattr(self, key, self.relocate_one(attr, box, self.__class__.box))


# database: regions & saved screenshot
class Regions(_Regions):
    """
    Store region(length 4) or point(length 2) data at screensize 1920*1080.
    """
    # only width and height are standalone int, others are Sequence
    width = 1920
    height = 1080
    box = (0, 0, width, height)  # left top right bottom

    # common, or for supervisor
    net_error = ((599, 814, 720, 872), (1138, 813, 1378, 876))
    safe_area = (1400, 40)
    menu_button = (1659, 974, 1911, 1074)

    # ---------- gacha part ----------
    gacha_point = (600, 650)
    gacha_tab = (1009, 188, 1213, 228)
    gacha_10_initial = (483, 630, 800, 774)
    gacha_reset_action = (1546, 337, 1863, 394)
    gacha_reset_confirm = (1097, 813, 1416, 879)
    gacha_reset_finish = (800, 811, 1113, 878)
    gacha_empty = (285, 631, 524, 780)  # used when no ticket left
    # move to mailbox
    mailbox_full_confirm = (1112, 822, 1463, 873)

    # in mailbox
    mailbox_back = (49, 34, 242, 100)
    mailbox_get_action = (1509, 535, 1810, 582)
    mailbox_get_all_action = (1524, 302, 1805, 354)  # WARNING: don't click
    # box_items = [(1272, 400), (1272, 600), (1272, 800), (1272, 980)]
    mailbox_items = [(1231, 365, 1314, 447), (1231, 558, 1314, 640), (1231, 751, 1314, 833), (1231, 944, 1314, 1026)]
    mailbox_first_checkbox = (1231, 365, 1314, 447)
    mailbox_first_icon = (162, 350, 300, 435)
    mailbox_first_xn = (507, 295, 574, 329)  # x1
    mailbox_first_xn2 = (564, 295, 584, 329)  # '0' of x10
    mailbox_check_column = (1231, 264, 1314, 1079)
    mailbox_drag_start = (1070, 914)
    mailbox_drag_end = (1070, 250)
    box_history = (365, 30, 522, 102)
    # from mailbox move to bag/enhancement
    bag_full_sell_action = (471, 689, 565, 740)
    bag_full_enhance_action = (907, 689, 1008, 736)

    # in bag
    bag_back = (49, 34, 242, 100)
    bag_select_start = (200, 350)
    bag_select_end = (1416, 1050)
    bag_sell_action = (1600, 975, 1870, 1047)
    bag_sell_confirm = (1181, 912, 1340, 968)
    bag_sell_finish = (875, 908, 1045, 966)

    # from bag to drawer
    shop_sell = (1352, 465, 1723, 552)
    shop_event_item_exchange = (1352, 239, 1723, 322)
    shop_event_banner_list = [(848, 168, 1525, 445), (848, 468, 1525, 745), (848, 768, 1525, 1045)]
    rewards_action = (1688, 29, 1872, 97)

    # ---------- battle part ----------
    apply_friend = (1692, 521, 1826, 588)
    apply_friend_deny = (464, 913)
    quest = (966, 295, 1149, 417)  # (937, 240, 1848, 360)
    quest_outer = (966, 246, 1149, 427)
    quest_c = (1600, 265)
    quest_master_avatar = (91, 835, 242, 997)
    # rewards = (1680, 33, 1868, 91)

    ap_time = (346, 1041, 366, 1072)
    apple_close = (900, 900, 1016, 952)
    apples = ((471, 177, 645, 359), (471, 397, 645, 579), (474, 621, 645, 803), (471, 840, 645, 861))
    apple_confirm = (1195, 802, 1313, 882)
    # support = ((72,489,1617,560), (72,790,1617,860))
    # 2 supports one time，support[svt][skill]
    loading_line = (10, 1057, 70, 1060)
    support_team_icon = (1637, 320, 1767, 384)
    support_team_icon_column = (1637, 245, 1767, 1000)
    support_class_icons = [(117, 175, 165, 209), (218, 175, 266, 209), (319, 175, 367, 209), (420, 175, 468, 209),
                           (521, 175, 569, 209), (622, 175, 670, 209), (723, 175, 771, 209), (824, 175, 872, 209),
                           (925, 175, 973, 209), (1026, 175, 1074, 209)]  # All, 7 common class, extra, mix
    support_scrollbar_start = (1857, 270)
    support_scrollbar_end = (1857, 1047)
    support_scrollbar_head = (1843, 274, 1873, 296)
    support_ce = ((72, 489, 316, 537), (72, 791, 316, 838))  # 礼装位置
    support_ce_max = ((273, 524, 303, 552), (273, 825, 303, 854))  # 礼装满破的星星
    support_skill = ((1252, 463, 1577, 548), (1252, 764, 1577, 847))  # 技能整体外轮廓
    support_skills = [[(1260, 468, 1334, 544), (1378, 468, 1448, 544), (1497, 468, 1562, 544)],
                      [(1260, 768, 1334, 844), (1378, 768, 1448, 844), (1497, 768, 1562, 844)]]  # 3个技能外轮廓
    support_skill_lvs = [[(1260, 511, 1300, 544), (1380, 511, 1420, 544), (1500, 511, 1540, 544)],
                         [(1260, 811, 1334, 844), (1380, 811, 1454, 844),
                          (1500, 811, 1574, 844)]]  # 3个lv, 强化箭头未比较, not used
    support_friend_icon = (1696, 484, 1741, 529)

    support_confirm_title = (821, 171, 1108, 230)
    support_refresh_confirm = (1110, 890)
    support_refresh = (1238, 160, 1318, 230)
    support_class_affinity = (1119, 160, 1201, 230)
    support_scroll = ((1860, 520), (1860, 640), (760, 880))

    team_start_action = (1655, 973, 1902, 1052)
    team_cloth = (20, 980, 263, 1054)
    wave_num = (1293, 18, 1320, 54)
    enemies_all = (0, 0, 1080, 128)
    enemies = ((0, 0, 120, 130), (360, 0, 480, 130), (720, 0, 840, 130))  # skill_to_enemies
    dying_clicking_point = (960, 360)
    skills = [
        [(61, 823, 121, 908), (202, 823, 262, 908), (343, 823, 403, 908)],
        [(539, 823, 599, 908), (680, 823, 740, 908), (821, 823, 881, 908)],
        [(1017, 823, 1077, 908), (1158, 823, 1218, 908), (1299, 823, 1359, 908)]
    ]
    skill_target_X = (430, 600, 580, 750)  # 第一个人
    skill_to_target = ((490, 700), (970, 700), (1429, 700))
    master_skill = (1736, 440, 1841, 507)
    master_skills = ((1319, 427, 1404, 512), (1450, 427, 1535, 512), (1581, 427, 1666, 512))
    loc_wave = [wave_num, master_skill]
    attack = (1599, 957, 1688, 1010)  # 大小可变的attack字样以下部分，且与cards_back不重叠
    cards_back = (1725, 1007, 1878, 1043)
    cards = (
        (84, 655, 303, 903), (466, 655, 685, 903), (848, 655, 1067, 903), (1235, 655, 1454, 903),
        (1624, 655, 1843, 903),
        (529, 204, 707, 441), (848, 204, 1026, 441), (1167, 204, 1345, 441))
    cards_outer = ((84, 500, 303, 1000), (466, 500, 685, 1000), (848, 500, 1067, 1000), (1235, 500, 1454, 1000),
                   (1624, 500, 1843, 1000),
                   (529, 100, 707, 510), (848, 100, 1026, 510), (1167, 100, 1345, 510))

    order_change = (
        (87, 403, 322, 643), (387, 403, 622, 643), (687, 403, 922, 643), (987, 403, 1222, 643), (1287, 403, 1522, 643),
        (1587, 403, 1822, 643))
    order_change_confirm = (739, 907, 1167, 974)  # length 6

    # kizuna = (115, 251, 580, 305)  # 与从者的羁绊text
    kizuna = (186, 646, 205, 665)  # 羁绊点数第一格
    finish_qp = (418, 884, 487, 955)
    rewards_show_num = (1593, 115, 1718, 149)
    rewards_items_outer = [[(233 + j * 206, 186 + i * 213, 409 + j * 206, 379 + i * 213) for j in range(0, 7)] for i in
                           range(0, 3)]
    rewards_items = [[(241 + j * 206, 196 + i * 213, 401 + j * 206, 290 + i * 213) for j in range(0, 7)] for i in
                     range(0, 3)]
    finish_next = (1444, 980, 1862, 1061)
    finish_craft = (454, 216, 623, 386)
    restart_quest_yes = (1122, 812, 1386, 829)
    # friend_point = (460, 810, 580, 880)

    # ============= fp gacha ================
    fp_gacha_logo = (962, 22, 1050, 100)
    fp_gacha10_button = (1111, 800, 1374, 886)
    fp_gacha_point = (1240, 864)
    fp_gacha_confirm = (1205, 819, 1300, 868)
    fp_gacha_result_summon = (987, 983, 1302, 1035)  # gacha10again, origin is(1096, 980, 1200, 1037)


class ImageTemplates:
    """
    Store loaded template images. Image file(*.png) should be screenshots token by PIL or mss module.
    Otherwise, image comparision may not work.
    @DynamicAttrs
    """

    def __init__(self, directory: str = None):
        self.directory: str = directory
        self.templates: Dict[str, Image.Image] = {}
        # ============ battle part ============
        self.net_error: Optional[Image.Image] = None
        self.apple_confirm: Optional[Image.Image] = None
        self.apple_page: Optional[Image.Image] = None
        self.apply_friend: Optional[Image.Image] = None
        self.cards1: Optional[Image.Image] = None
        self.cards2: Optional[Image.Image] = None
        self.cards3: Optional[Image.Image] = None
        self.cards4: Optional[Image.Image] = None
        self.rewards: Optional[Image.Image] = None
        self.kizuna: Optional[Image.Image] = None
        self.order_change: Optional[Image.Image] = None
        self.quest: Optional[Image.Image] = None
        self.team: Optional[Image.Image] = None
        self.restart_quest: Optional[Image.Image] = None
        self.support: Optional[Image.Image] = None
        self.support_confirm: Optional[Image.Image] = None
        self.wave1a: Optional[Image.Image] = None
        self.wave1b: Optional[Image.Image] = None
        self.wave2a: Optional[Image.Image] = None
        self.wave2b: Optional[Image.Image] = None
        self.wave3a: Optional[Image.Image] = None
        self.wave3b: Optional[Image.Image] = None
        # ============ gacha part ============
        self.gacha_initial: Optional[Image.Image] = None
        self.gacha_empty: Optional[Image.Image] = None
        self.gacha_reset_confirm: Optional[Image.Image] = None
        self.gacha_reset_finish: Optional[Image.Image] = None
        self.mailbox_full_alert: Optional[Image.Image] = None
        self.mailbox_unselected1: Optional[Image.Image] = None
        self.mailbox_unselected2: Optional[Image.Image] = None
        self.mailbox_selected: Optional[Image.Image] = None
        self.bag_full_alert: Optional[Image.Image] = None
        self.bag_unselected: Optional[Image.Image] = None
        self.bag_selected: Optional[Image.Image] = None
        self.bag_sell_confirm: Optional[Image.Image] = None
        self.bag_sell_finish: Optional[Image.Image] = None
        self.shop: Optional[Image.Image] = None
        self.shop_event_banner_list: Optional[Image.Image] = None
        # ============ fp gacha part ============
        self.fp_gacha_page: Optional[Image.Image] = None
        self.fp_gacha_confirm: Optional[Image.Image] = None
        self.fp_gacha_result: Optional[Image.Image] = None
        self.fp_bag1_full: Optional[Image.Image] = None
        self.fp_bag2_full: Optional[Image.Image] = None
        # =========== End Props =========== #
        if directory is not None:
            self.read_templates(directory)

    def read_templates(self, directory: str, append=False):
        if not append:
            self.templates = {}
        for filename in os.listdir(directory):
            if not filename.endswith('.png'):
                continue
            filepath = os.path.join(directory, filename)
            key = filename[0:len(filename) - 4]
            self.templates[key] = Image.open(filepath)
            self.__dict__[key] = self.templates[key]
        self.directory = directory

    def __repr__(self):
        return f'{self.__class__.__name__}(dir="{self.directory}", templates={self.templates})'

    def __getattr__(self, item):
        """if @property item is not defined, then search item in self.templates"""
        # could be removed?
        if item in self.templates:
            return self.templates[item]
        else:
            raise AttributeError(f'{item} for class {self.__class__.__name__}')

    def get(self, item, k=None):
        # type:(Union[str, Sequence[str]],Image.Image)-> Union[Image.Image, Sequence[Image.Image]]
        """get one item or a list of items"""
        if isinstance(item, str) and item in self.templates:
            return self.templates[item]
        elif isinstance(item, (list, tuple)):
            # cannot use Sequence instead (list, tuple), str is also Sequence
            return [self.templates[i] for i in item]
        else:
            return k
