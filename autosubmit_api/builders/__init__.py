class BaseBuilder:
    """
    Default Base Builder
    Reference: https://refactoring.guru/design-patterns/builder
    """

    def __init__(self, reset_after_produce=False) -> None:
        self._reset_after_produce = reset_after_produce
        self.reset()

    def reset(self):
        self._product = None

    @property
    def product(self):
        product = self._product
        if self._reset_after_produce:
            self.reset()
        return product
