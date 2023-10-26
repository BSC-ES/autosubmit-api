from .populate_details.populate import DetailsProcessor
from ..config.basicConfig import APIBasicConfig

APIBasicConfig.read()

def main():
  DetailsProcessor(APIBasicConfig).process()

if __name__ == "__main__":
  main()