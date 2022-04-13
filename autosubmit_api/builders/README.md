Some of the main `API` classes follow the `Composition` pattern. As a consequence, they require that dependencies are prepared. To avoid cluttering the code that requires these classes, we make use of the `Builder` pattern, where a `Director` class uses a `Builder` class to generate an object that contains the necessary dependencies. These builders are stored in this folder.

There are other classes in the project that might require the introduction of their own builders. I suggest we keep all builder inside this folder.
