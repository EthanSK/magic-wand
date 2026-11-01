import Foundation
let host="var WandSenseHost={create:function(g,n){return {repl:function(s){var a=JSON.parse(s);n.text(a[0],a[1]);},teardown:function(){}}}};"
let source=WandVirtualPuck.Sources(shim:"",host:host,base:"",bridge:"",power:"")
let v=WandVirtualPuck(sources:source)!
var text="",times:[Double]=[]
v.onTimedText={text += $0;times += $1}
v.send("[\"@RAW 9615,500,0,0\",1.0]")
v.send("[\"@BOTTOM 0\",1.1]")
v.send("[\"@WAND 20,10,0\",1.2]")
v.discardPendingPointerMotion()
v.send("[\"@RAW 9615,7,0,0\",2.0]")
RunLoop.main.run(until:Date().addingTimeInterval(0.03))
precondition(text=="@BOTTOM 0\n@WAND 0,0,0\n@RAW 9615,7,0,0\n")
precondition(times==[1.1,1.2,2.0],"timestamps survive batching and cancellation in order")
v.teardown()
print("PASS: event timestamps survive batching and cancellation without replay")
