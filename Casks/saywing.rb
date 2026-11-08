cask "saywing" do
  version "0.1.33,133"

  on_arm do
    sha256 "62203c36b4f5d336395b01f51dafe9c52de00750b17791c1fe02bad0c0a5e2b7"

    url "https://www.christopherboebel.com/downloads/saywing/Saywing-#{version.csv.first}-#{version.csv.second}.dmg"
  end
  on_intel do
    sha256 "ca08952a23c85680a675406693a419b0c9b7e86a08bcba82f258e611ede81d83"

    url "https://www.christopherboebel.com/downloads/saywing/x86_64/Saywing-#{version.csv.first}-#{version.csv.second}.dmg"
  end

  name "Saywing"
  desc "Reads on-screen text aloud and transcribes speech, fully on-device"
  homepage "https://github.com/ChrBoebel/saywing"

  livecheck do
    url "https://www.christopherboebel.com/downloads/saywing/latest.json"
    strategy :json do |json|
      version = json["version"]
      build = json["build"]
      next if version.blank? || build.blank?

      "#{version},#{build}"
    end
  end

  auto_updates true
  depends_on macos: :sonoma

  app "Saywing.app"

  zap trash: [
    "~/Library/Application Support/Saywing",
    "~/Library/Caches/com.christopherbobel.OpenScreenReader",
    "~/Library/HTTPStorages/com.christopherbobel.OpenScreenReader",
    "~/Library/Preferences/com.christopherbobel.OpenScreenReader.plist",
  ]
end
