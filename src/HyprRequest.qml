import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import "DuckModel.js" as Model

// One short connection per request. Never leave Hyprland's command socket open.
Scope {
    id: request
    property string socketPath: Hyprland.requestSocketPath
    property bool busy: false
    property string command: ""
    property int expected: 1
    property string buffer: ""
    property var response: null
    property string failure: ""
    property int count: 0
    property int failures: 0
    signal completed(var values)
    signal failed(string message)

    function send(command,expected) {
        if(busy||socket.connected||!socketPath)return false;
        request.command=command;request.expected=expected||1;
        buffer="";response=null;failure="";busy=true;count++;
        timeout.restart();socket.connected=true;return true;
    }
    function abort(message) {
        if(!busy)return;
        failure=message;socket.connected=false;
        if(!socket.connected)finish();
    }
    function finish() {
        if(!busy)return;
        timeout.stop();busy=false;
        if(response!==null)completed(response);
        else{failures++;failed(failure||"Hyprland closed an incomplete response");}
    }
    Socket {
        id: socket
        path: request.socketPath
        onConnectedChanged: {
            if(connected){write(request.command);flush();}
            else request.finish();
        }
        onError: function(error) {if(request.response===null)request.abort("Hyprland socket: "+error);}
        parser: SplitParser {
            splitMarker: ""
            onRead: function(chunk) {
                if(!request.busy)return;
                request.buffer+=chunk;
                if(request.buffer.length>1048576){request.abort("Hyprland response is too large");return;}
                try{request.response=Model.parseValues(request.buffer,request.expected);}catch(e){return;}
                socket.connected=false;
            }
        }
    }
    Timer {id:timeout;interval:750;onTriggered:request.abort("Hyprland request timed out");}
    Component.onDestruction: socket.connected=false
}
