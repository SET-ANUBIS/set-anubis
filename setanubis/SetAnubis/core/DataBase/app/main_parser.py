from SetAnubis.core.DataBase.adapters.UFOParser import UFOParser
import os

if __name__ == "__main__":
    test = UFOParser()
    result = test.parse(os.path.join(os.path.dirname(__file__), "..", "..", "UFOInterface", "SM_NLO", "particles.py"))
    # test.parse("db/SM/SM_NLO/particles.py")
    print(result)