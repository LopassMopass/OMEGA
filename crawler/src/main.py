"""
main.py

Entry point managing crawler and writer threads execution.
"""

import threading
import queue
from crawler.src.writer.writer import writer_thread
#from crawler.src.crawlers.gigacomputer_crawler import GigacomputerCrawler
# Uncomment to use additional crawlers:
# from crawler.src.crawlers.alza_crawler import AlzaCrawler
# from crawler.src.crawlers.datart_crawler import DatartCrawler
# from crawler.src.crawlers.planeo_crawler import PlaneoCrawler
from crawler.src.crawlers.stolnipocitace_crawler import StolniPocitaceCrawler
# from crawler.src.crawlers.pocitarna_crawler import PocitarnaCrawler

def main():
    """
    Main function initiating crawler and writer threads.
    """
    data_queue = queue.Queue()

    write_done_events = {
        #"gigacomputer": threading.Event(),
        # "alza": threading.Event(),
        # "datart": threading.Event(),
        # "planeo": threading.Event(),
         "stolnipocitace": threading.Event(),
        # "pocitarna": threading.Event()
    }

    for event in write_done_events.values():
        event.set()

    writer_t = threading.Thread(target=writer_thread, args=(data_queue, write_done_events), daemon=True)
    writer_t.start()

    #gigacomputer_crawler = GigacomputerCrawler("gigacomputer", data_queue, write_done_events["gigacomputer"])
    #gigacomputer_t = threading.Thread(target=gigacomputer_crawler.crawl, daemon=True)
    #gigacomputer_t.start()
    #gigacomputer_t.join()

    stolnipocitace_crawler = StolniPocitaceCrawler("stolnipocitace", data_queue, write_done_events["stolnipocitace"])
    stolnipocitace_t = threading.Thread(target=stolnipocitace_crawler.crawl, daemon=True)
    stolnipocitace_t.start()
    stolnipocitace_t.join()

    data_queue.put(("STOP", None))
    writer_t.join()

    print("Main: All threads have finished.")

if __name__ == "__main__":
    main()
