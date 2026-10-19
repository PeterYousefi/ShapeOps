import json, sys
import cadquery as cq
from backend.cad import describe
if __name__=='__main__':
    try:
        shape=cq.importers.importStep(sys.argv[1]).val()
        result=describe(shape)
        print('SHAPEOPS_RESULT:'+json.dumps(result))
    except Exception:
        print('SHAPEOPS_RESULT:'+json.dumps({'error':'STEP could not be processed as valid supported solid geometry.'}))
        sys.exit(2)
