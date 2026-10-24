import Foundation

/// A sensor zero belongs to one physical wand, not a control version or grip.
/// Ethan calls this "save it from the known devices": reuse the last valid zero
/// after reconnect/power-on without asking for another manual calibration.
struct WandCalibration: Codable, Equatable {
    let x:Double,y:Double,z:Double
    var valid:Bool {[x,y,z].allSatisfy{$0.isFinite && abs($0)<=8*134}}
    var json:String? {
        guard valid,let data=try? JSONEncoder().encode(self) else{return nil}
        return String(data:data,encoding:.utf8)
    }
}
struct WandCalibrationRecord:Codable {
    let schemaVersion:Int
    let device:String
    let bias:WandCalibration
}
enum WandCalibrationStore {
    static func read(_ url:URL,device:String)->WandCalibration? {
        guard let attr=try? FileManager.default.attributesOfItem(atPath:url.path),
              attr[.type] as? FileAttributeType == .typeRegular,
              let size=attr[.size] as? NSNumber,size.intValue<=4096,
              let data=try? Data(contentsOf:url),
              let record=try? JSONDecoder().decode(WandCalibrationRecord.self,from:data),
              record.schemaVersion==1,record.device==device,record.bias.valid else{return nil}
        return record.bias
    }
    static func write(_ bias:WandCalibration,to url:URL,device:String)throws {
        guard bias.valid else{throw CocoaError(.fileWriteInvalidFileName)}
        try FileManager.default.createDirectory(at:url.deletingLastPathComponent(),withIntermediateDirectories:true,attributes:[.posixPermissions:0o700])
        let record=WandCalibrationRecord(schemaVersion:1,device:device,bias:bias)
        let data=try JSONEncoder().encode(record)
        try data.write(to:url,options:.atomic)
        try FileManager.default.setAttributes([.posixPermissions:0o600],ofItemAtPath:url.path)
    }
}
