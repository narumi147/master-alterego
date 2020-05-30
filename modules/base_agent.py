import threading

from util.addon import check_sys_setting, raise_alert
from util.autogui import *
from .server import app


class BaseAgent:
    _server_thread: threading.Thread = None

    def __init__(self):
        self.T = None
        self.LOC = None

    def pre_process(self, cfg):
        config.load(cfg)
        check_sys_setting(config.need_admin)
        if config.www_host_port is not None:
            self.run_sever(*config.www_host_port)

    def post_process(self):
        # server thread should be daemon, make it possible to be terminated by Ctrl-C
        # in terminal: keep app running until ctrl-C pressed => call thread.join() in post processing
        # in interactive: main thread is always alive, join() is not needed, we can terminate it manually.
        if config.hide_when_finish:
            pyautogui.hotkey('alt', 'z')  # hide window for MuMu emulator
        if not is_interactive_mode() and self._server_thread.is_alive():
            logger.info('keep running server...')
            self._server_thread.join()

    @classmethod
    def terminate_server(cls):
        from util.addon import kill_thread
        kill_thread(cls._server_thread)
        app.logger.info(f'server stopped: {cls._server_thread}')

    @classmethod
    def run_sever(cls, host='0.0.0.0', port=8080):
        if cls._server_thread is not None and cls._server_thread.is_alive():
            app.logger.info(f'server is already running: {cls._server_thread}')
            return
        cls._server_thread = threading.Thread(target=app.run, name='flask_app_server', args=[host, port], daemon=False)
        cls._server_thread.start()
        app.logger.info(f'server started: {cls._server_thread}')

    def sell(self, num=100, duration=1, up_time=1):
        """
        Start at sell svt page, at last click BACK once to the page with menu button.
        If num<=0: manual mode; num>0: sell times.
        """
        T, LOC = self.T, self.LOC
        logger.info('selling...', extra=LOG_TIME)
        wait_targets(T.bag_unselected, LOC.bag_svt_tab)
        print('Make sure the correct setting of **FILTER**')
        if num <= 0:
            logger.info('need manual operation!')
            time.sleep(2)
            config.update_time(config.manual_operation_time)  # min for manual operation
            raise_alert()
            wait_targets(T.shop, LOC.menu_button)
            return

        no = 0
        while True:
            wait_targets(T.bag_unselected, [LOC.bag_svt_tab, LOC.bag_sell_action])
            if no < num:
                drag(LOC.bag_select_start, LOC.bag_select_middle, 0.6, 0.5, None, 0)
                drag(LOC.bag_select_middle, LOC.bag_select_end, duration, None, up_time)
            page_no = wait_which_target([T.bag_selected, T.bag_unselected],
                                        [LOC.bag_sell_action, LOC.bag_sell_action])
            if page_no == 0:
                no += 1
                logger.info(f'sell: {no} times...', extra=LOG_TIME)
                click(LOC.bag_sell_action)
                wait_targets(T.bag_sell_confirm, LOC.bag_sell_confirm, at=0)
                wait_targets(T.bag_sell_finish, LOC.bag_sell_finish, at=0)
            else:
                if no == 0:
                    logger.warning('svt bag full but nothing can be sold! waiting manual operation.')
                    config.update_time(config.manual_operation_time)
                    raise_alert()
                    wait_targets(T.shop, LOC.menu_button)
                    return
                logger.info('all sold.', extra=LOG_TIME)
                click(LOC.bag_back)
                wait_targets(T.shop, LOC.menu_button)
                return