"""One naming policy separates printable trials from preparation-only meshes."""
def normal_name(part):
    return part+'-SOURCE-REQUIRES-PREPARATION.stl'

def project_name(directory):
    return ('PRINT-FIRST-Pyramid-Key-Test.3mf' if directory.name=='trial-Key_Carrier'
            else 'PRINT-FIRST-Key-Clip-Test.3mf' if directory.name.startswith('fit-coupon')
            else 'AFTER-KEY-TEST-Pyramid-Holder-R14.3mf')
