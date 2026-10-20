start cmd /c "am_install_tree -u=infodba -p=infodba -g=dba -operation=export -path=E:\plmapps\MayaConfig\PreUpgradeChecks\AccessManager.xml -format=xml"

start cmd /c "preferences_manager -u=infodba -p=infodba -g=dba -scope=SITE -mode=export -out_file=E:\plmapps\MayaConfig\PreUpgradeChecks\preferences.xml"

start cmd /c "plmxml_export -u=infodba -p=infodba -g=dba -xml_file=E:\plmapps\MayaConfig\PreUpgradeChecks\organization.xml -class=Group"
        
start cmd /c "index_verifier -u=infodba -p=infodba -g=dba -o=DRYRUN > E:\plmapps\MayaConfig\PreUpgradeChecks\missing_indices.sql"


backup_xmlinfo -u=infodba -p=infodba -g=dba
move .\backup.xml E:\plmapps\MayaConfig\PreUpgradeChecks\
move .\backup.dtd E:\plmapps\MayaConfig\PreUpgradeChecks\
