from .addon import *
from .autogui import *
from .config import *
from .log import *


def supervise_log_time(thread, timeout=60, interval=10, alert_type=None, alert_loops=15):
    # type: (threading.Thread,float,float,bool,int)->None
    assert thread is not None, thread
    config.task_thread = thread
    if alert_type is None:
        alert_type = config.alert_type

    def _overtime():
        return config.get_dt() > timeout

    logger.info(f'start supervising thread {thread.name}, timeout={timeout}')
    thread.start()
    while not thread.is_alive():
        time.sleep(0.01)
    logger.info(f'Thread-{thread.ident}({thread.name}) started...')
    config.update_time()
    # from here, every logging should have arg: NO_LOG_TIME, otherwise endless loop.
    loops = alert_loops
    while True:
        # every case: stop or continue
        # case 1: thread finished normally - stop supervision, check this first
        if config.task_finish_signal:
            message, mail_level = config.task_finish_signal
            # thread finished: all battles finished(thread exit normally)
            logger.info(f'Thread-{thread.ident}({thread.name}) finished. Stop supervising.')
            send_mail(f'[{thread.name}] {message}', level=mail_level or MailLevel.info)
            # make sure thread is stopped
            if thread.is_alive():
                kill_thread(thread)
            break
        # case 2: all right - continue supervision
        if thread.is_alive() and not _overtime():
            loops = alert_loops  # reset loops
            time.sleep(interval)
            continue
        # case 3: thread terminated but not finished task
        if config.task_finish_signal is None and config.task_thread and not config.task_thread.is_alive():
            logger.warning(f'thread terminated unexpectedly...')
            loops = -1
        else:
            T: ImageTemplates = config.T
            LOC: Regions = config.LOC
            # case 4: task alive and network error - click "retry" and continue
            img_net, loc_net = T.net_error, LOC.net_error
            if img_net is not None and loc_net is not None:
                shot = screenshot()
                if match_targets(shot, img_net, loc_net[0]) and match_targets(shot, img_net, loc_net[1]):
                    logger.warning('Network error! click "retry" button')
                    click(loc_net[1], lapse=3)
                    config.update_time(60)
                    continue

            # case 5: svt status window is popped unexpectedly when execute svt skill(actually not executed yet)
            if T.svt_status_window is not None:
                if match_targets(screenshot(), T.svt_status_window, LOC.svt_status_window_close):
                    screenshot().save(f'img/crash/svt_status_window_error_{time.time()}.png')
                    xy = config.temp.get('click_xy', (0, 0))  # skill location last clicked
                    logger.warning(f'Servant status window is popped unexpectedly! Re-click at {xy}')
                    click(LOC.svt_status_window_close, 2)
                    click(xy)
                    config.update_time(30)

            # case 6: task alive and need re-login after 3am in jp server
            # if match menu button, click save_area until match quest1234, click 1234
            if callable(config.battle.login_handler):
                config.battle.login_handler()

            # case 7: task alive but unrecognized error - waiting user to handle (in 2*loops seconds)
            if loops == alert_loops:
                logger.warning(f'Something wrong, please solve it, or it will be force stopped...\n'
                               f' - thread  alive: {thread.is_alive()}.\n'
                               f' - finish signal: {config.task_finish_signal}.\n'
                               f' - last log time: {time.asctime()}')
                # if click event is not submitted actually, try click again.
                click()
        if loops >= 0:
            print(f'\rcount down {loops}...', end='\r')
        loops -= 1
        if alert_type:
            beep(1, 2)
        else:
            time.sleep(3)
        if loops < 0:
            # not solved! kill thread and stop.
            if thread.is_alive():
                kill_thread(thread)
            err_msg = f'{thread}:\n' \
                      f' - finish signal: {config.task_finish_signal}\n' \
                      f' - current  time: {time.asctime()}\n' \
                      f' - last log time: {time.asctime(time.localtime(config.log_time))}\n' \
                      f' - over time: {time.time() - config.log_time:.2f} secs (timeout={timeout}).\n'
            send_mail(err_msg, subject=f'[{thread.name}]Went wrong!', level=MailLevel.error)
            break
    raise_alert(alert_type, loops=10)
    logger.info('exit supervisor.')


def start_loop(func: Callable):
    config.new_task_signal = True
    while True:
        if not config.new_task_signal:
            time.sleep(5)
        else:
            config.new_task_signal = False
            func()
            logger.info('waiting new task...')
            if config.www_host_port is not None:
                host, port = (config.www_host_port + [None, None])[:2]
                logger.info(f'Server is running on http://{host or "0.0.0.0"}:{port or 8180}')
