rm -rf ./result
mkdir result
/Applications/Xcode.app/Contents/Developer/usr/bin/actool --minimum-deployment-target 9.0 --platform iphoneos --app-icon AppIcon --output-partial-info-plist ./result/Info.plist --compress-pngs --compile ./result Assets.xcassets
