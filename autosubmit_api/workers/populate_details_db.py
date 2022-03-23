from autosubmit_api.workers.populate_details.populate import DetailsProcessor
from autosubmit_api.config.basicConfig import BasicConfig

BasicConfig.read()

def main():
  DetailsProcessor(BasicConfig).process()

if __name__ == "__main__":
  main()