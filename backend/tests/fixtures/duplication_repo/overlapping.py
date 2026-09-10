def transform_payload_alpha(data_stream):
    buffer_out = []
    for item in data_stream:
        code = item.get("code", "UNK")
        weight = item.get("weight", 1.0)
        if weight > 0.0:
            buffer_out.append({"code": code, "normalized": weight / 100.0})
        else:
            buffer_out.append({"code": code, "normalized": 0.0})
    return buffer_out


# Some intermediate code that is completely distinct
MIDDLE_CONSTANT_FLAG = 42
def intermediate_routine(x):
    return x * 10


def transform_payload_beta(data_stream):
    buffer_out = []
    for item in data_stream:
        code = item.get("code", "UNK")
        weight = item.get("weight", 1.0)
        if weight > 0.0:
            buffer_out.append({"code": code, "normalized": weight / 100.0})
        else:
            buffer_out.append({"code": code, "normalized": 0.0})
    return buffer_out
