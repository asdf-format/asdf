# We ignore these files because these modules create deprecation warnings on
# import. When warnings are turned into errors this will completely prevent
# test collection
collect_ignore = ["stream.py"]
