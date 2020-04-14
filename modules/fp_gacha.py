from util.autogui import *
from util.supervisor import supervise_log_time


class FpGacha:
    def __init__(self, path=None):
        self.T = ImageTemplates(path)
        self.LOC = Regions()

    def pre_process(self, conf=None):
        config.load(conf)
        check_sys_admin()
        self.T.read_templates(config.fp_gacha.dir)
        config.T = self.T
        config.LOC = self.LOC
        config.log_file = f'logs/gacha.full.log'

    def start(self, supervise=True, conf=None):
        self.pre_process(conf)
        logger.info('start friend point gacha...')
        start_func = self.draw
        time.sleep(2)
        if supervise:
            t_name = os.path.basename(config.fp_gacha.dir)
            thread = threading.Thread(target=start_func, name=t_name, args=[config.fp_gacha.num], daemon=True)
            config.running_thread = thread
            supervise_log_time(thread, 30, interval=3)
        else:
            start_func(config.fp_gacha.num)

    def draw(self, num=100):
        """
        :param num: times of gacha10(2000fp)
        """
        T = self.T
        LOC = self.LOC

        logger.info('gacha: starting...')
        loops = 0
        while loops < num:
            # print(f'\r loop {loops:<4d}', end='')
            config.log_time = time.time()
            if loops % 5 == 0:
                logger.debug(f'fp gacha {loops}/{num}...')
            loops += 1
            wait_targets(T.fp_gacha_page, [LOC.fp_gacha_logo, LOC.fp_gacha10_button], at=LOC.fp_gacha10_button)
            page_no = wait_which_target([T.fp_gacha_result, T.fp_bag2_full],
                                        [LOC.fp_gacha_result_summon, LOC.bag_full_sell_action],
                                        clicking=LOC.fp_gacha_point, interval=0.01)
            if page_no == 0:
                click(LOC.fp_gacha_result_summon)
                config.count_fp_gacha()
            elif page_no > 0:
                logger.info(f'bag {page_no} full, sell or enhance manually.')
                config.log_time = time.time() + config.manual_operation_time
                raise_alert(loops=1)
                wait_targets(T.fp_gacha_page, [LOC.fp_gacha_logo, LOC.fp_gacha10_button])
                logger.info('back to fp gacha.')
