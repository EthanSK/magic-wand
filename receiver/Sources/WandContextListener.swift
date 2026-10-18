import Foundation
import AppKit
import Darwin

final class WandContextListener {
    private var fd:Int32 = -1
    private var source:DispatchSourceRead?
    var onChange:((Bool)->Void)?
    var onModeChange:((String?)->Void)?
    var onReviewChange:((String?)->Void)?
    private var reviewMode:String?
    private(set) var appMode:String?
    private var expiry:DispatchWorkItem?
    private var reported=false
    private var active=false, received=Date.distantPast
    private var appPID:Int32=0
    private let path=FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/WandReceiver/context.sock").path
    var isActive:Bool {active && Date().timeIntervalSince(received)<0.8 && kill(appPID,0)==0}
    func start() {
        var info=stat()
        if lstat(path,&info)==0 {
            guard info.st_uid==geteuid(),info.st_mode & S_IFMT == S_IFSOCK else{return}
            unlink(path)
        }
        fd=socket(AF_UNIX,SOCK_DGRAM,0);guard fd>=0 else{return}
        var address=sockaddr_un();address.sun_family=sa_family_t(AF_UNIX)
        let bytes=Array(path.utf8)+[0];guard bytes.count<=MemoryLayout.size(ofValue:address.sun_path) else{return}
        withUnsafeMutableBytes(of:&address.sun_path){$0.copyBytes(from:bytes)}
        address.sun_len=UInt8(MemoryLayout<sockaddr_un>.size)
        let result=withUnsafePointer(to:&address){$0.withMemoryRebound(to:sockaddr.self,capacity:1){bind(fd,$0,socklen_t(MemoryLayout<sockaddr_un>.size))}}
        guard result==0 else{close(fd);fd = -1;return}
        chmod(path,0o600);_=fcntl(fd,F_SETFL,O_NONBLOCK)
        let reader=DispatchSource.makeReadSource(fileDescriptor:fd,queue:.main)
        reader.setEventHandler{[weak self] in self?.read()};reader.resume();source=reader
    }
    private func read() {
        var bytes=[UInt8](repeating:0,count:1024)
        while true {
            let n=recv(fd,&bytes,bytes.count,0);if n<=0{return}
            guard n<=512,let v=(try? JSONSerialization.jsonObject(with:Data(bytes.prefix(n)))) as? [String:Any],
                  v["version"] as? Int == 1, let a=v["active"] as? Bool,
                  let pid=v["pid"] as? Int32,let time=v["sentAt"] as? Double,
                  abs(Date().timeIntervalSince1970-time)<0.8,
                  let app=NSRunningApplication(processIdentifier:pid),
                  app.bundleURL?.standardizedFileURL.path == "/Applications/AgenticMouse.app" else {continue}
            active=a;appPID=pid;received=Date()
            let rawMode=v["appMode"] as? String ?? ""
            let mode=a && !rawMode.isEmpty && rawMode.count<=32 && rawMode.allSatisfy({$0.isLetter}) ? rawMode : nil
            if mode != appMode {appMode=mode;onModeChange?(mode)}
            if reported != isActive {reported=isActive;onChange?(reported)}
            let rawReview = v["reviewMode"] as? String ?? ""
            let nextReview = a && ["changes","files"].contains(rawReview) ? rawReview : nil
            if nextReview != reviewMode {reviewMode=nextReview;onReviewChange?(nextReview)}
            expiry?.cancel()
            let task=DispatchWorkItem{[weak self] in
                guard let self else{return}
                if self.reported && !self.isActive {self.reported=false;self.onChange?(false);if self.reviewMode != nil {self.reviewMode=nil;self.onReviewChange?(nil)};if self.appMode != nil {self.appMode=nil;self.onModeChange?(nil)}}
            }
            expiry=task;DispatchQueue.main.asyncAfter(deadline:.now()+0.9,execute:task)
        }
    }
    deinit{source?.cancel();if fd>=0{close(fd)};unlink(path)}
}
