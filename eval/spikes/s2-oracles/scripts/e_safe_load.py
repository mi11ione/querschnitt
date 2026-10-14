"""Task E: load the BFH vectorizer pickle with an allow-listed Unpickler (refuses any class outside known libraries)."""
import collections
import io
import pickle
import sys

ALLOW_PREFIX = ("sklearn.", "numpy", "scipy.", "spacy.", "thinc.", "confection", "annif.analyzer", "srsly",
                "cymem", "preshed", "murmurhash", "blis", "catalogue", "collections", "copyreg", "pathlib",
                "_codecs", "weasel", "wasabi", "pydantic")
ALLOW_BUILTINS = {"getattr", "set", "frozenset", "dict", "list", "tuple", "slice", "bytearray", "bytes", "complex",
                  "object", "float", "int", "str", "bool", "type", "range"}
seen = collections.Counter()
SAFE_STD = {("functools", "partial"), ("re", "_compile"), ("re", "compile"), ("operator", "attrgetter"), ("operator", "itemgetter")}


class SafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        seen[(module, name)] += 1
        if module == "builtins" and name in ALLOW_BUILTINS:
            return super().find_class(module, name)
        if module.startswith(ALLOW_PREFIX) or module in ("numpy",):
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"refused global {module}.{name}")


def load(path):
    # joblib writes numpy arrays with its own NumpyArrayWrapper; fall back to joblib's unpickler subclass if needed
    with open(path, "rb") as f:
        head = f.read(4096)
    if b"joblib.numpy_pickle" in head or True:
        import joblib.numpy_pickle as jnp

        class SafeJoblib(jnp.NumpyUnpickler):
            def find_class(self, module, name):
                seen[(module, name)] += 1
                if module.startswith("joblib.numpy_pickle"):
                    return super().find_class(module, name)
                if module == "builtins" and name in ALLOW_BUILTINS:
                    return super().find_class(module, name)
                if module.startswith(ALLOW_PREFIX) or (module, name) in SAFE_STD:
                    return super().find_class(module, name)
                raise pickle.UnpicklingError(f"refused global {module}.{name}")

        with open(path, "rb") as f:
            u = SafeJoblib(path, f, ensure_native_byte_order="auto", mmap_mode=None)
            obj = u.load()
        return obj


if __name__ == "__main__":
    v = load(sys.argv[1])
    print(type(v), {k: c for k, c in seen.items()})
