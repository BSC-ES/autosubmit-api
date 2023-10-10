from .populate_details.populate import DetailsProcessor
from ..config.basicConfig import BasicConfig

BasicConfig.read()

def main():
  DetailsProcessor(BasicConfig).process()

if __name__ == "__main__":
  main()