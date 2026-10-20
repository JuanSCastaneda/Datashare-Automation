import logging
from DatabaseEditor.OracleEditor import OracleEditor
from UpgradeUtility.UpgradePrechecker import UpgradePreChecker

def main(staging_dir= "E:\\plmapps\\MayaConfig", configuration_file="Configuration\\configuration.json", u: str = None, p: str = None):
    header = "Upgrade Pre-Checker Utility"
    w = 150
    print(f"{"="*w}\n{' '*int((w - len(header))/2) }{header}\n{"="*w}\n{"="*w}\n")

    cases: dict[str, int] = dict()
    upgradePC: UpgradePreChecker = UpgradePreChecker(staging_dir, configuration_file, u, p)
    oracleEditor = OracleEditor()

    # DATABASE
    try:
        print(f"Checking SQL Pre-Requisites\n{w * '='}\n")
        print(f"\nChecking Version\n{w * '-'}\n")
        oracleEditor.checkOracleVersion()

        print(f"\nChecking UNDOTBS1\n{w * '-'}\n")
        oracleEditor.checkUNDOTBS1size()

        print(f"\nProviding Size Estimate\n{w * '-'}\n")
        oracleEditor.provideUpgradeSizeEst()

        cases["Database Checks"] = 1
    except Exception as e:

        logging.error(f"Could not connect to database: {e}")
        cases["Database Checks"] = 0
    
    # EXPORT
    # print(f"\n\nChecking Exporting Teamcenter Pre-Requisites\n{w * '='}")
    # try:
    #     upgradePC.exportAdminData()
    # except:
    #     logging.error("Failed to export all material")
    #     return
    
    # CONNECTIVITY
    print(f"\n\nChecking Database Connectivity\n{w * '-'}")
    try:
        upgradePC.checkDatabaseConnectivity()
        cases["Database Connectivity Check"] = 1
    except Exception as e:
        logging.error(f"Could not check database connectivity: {e}")
        cases["Database Connectivity Check"] = 0

    #INDICES
    print(f"\n\nChecking For Missing Indices\n{w * '-'}")
    try:
        upgradePC.checkMissingIndices()
        cases["Missing Indices Checks"] = 1
    except Exception as e:
        logging.error(f"Could not check for missing indices: {e}")
        cases["Missing Indices Checks"] = 0

    # ORGANIZATION
    print(f"\n\nChecking Organization\n{w * '-'}")
    try:
        upgradePC.checkOrganization()
        cases["Organization Check"] = 1
    except Exception as e:
        logging.error(f"Could not validate organization {e}")
        cases["Organization Check"] = 0

    # PREFERENCES
    print(f"\n\nChecking Preferences\n{w * '-'}")
    try:
        upgradePC.checkPreferences()
        cases["Preference Checks"] = 1
    except Exception as e:
        logging.error(f"Could not validate all preferences, please look above. {e}")
        cases["Preference Checks"] = 0

    width = 30
    for i, (k, v) in enumerate(cases.items()):
        print(f"[{i + 1}] {' ' * (width - len(k))}{k}: {"Success" if v == 1 else "Failed"}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format=" %(asctime)s [%(levelname)s] %(message)s",
                        datefmt='%H:%M:%S')
    main()