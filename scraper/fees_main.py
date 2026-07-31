from .fees import REGISTRY
from .fees.pipeline import scrape_all_fees, write_fees


def main():
    results = scrape_all_fees(REGISTRY)
    write_fees(results)


if __name__ == "__main__":
    main()
