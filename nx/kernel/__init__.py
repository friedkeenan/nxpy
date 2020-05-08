from ..types import Result

def result(desc_str):
    real_desc = {
        "NotFound": 121,
    }[desc_str]

    return Result(module=1, description=real_desc)