// jshint unused:false
// ^ this should only be added AFTER successfull check (disables waring for global functions)

/**
 * Update the Progress bar with the percentange of progress made in Analysing the Firmware
 * @param {*} percent Percentage Completed
 * @param {*} cur_ID Current Id of the Container
 */
 function makeProgress(percent, cur_ID) {
    "use strict";
    var rounded = Math.round(percent);
    var id = "#pBar_" + cur_ID;
    $(id).attr('aria-valuenow', rounded).css('width', rounded + '%').text(rounded + '%');
}

/**
 * Bind the Phase Messages from log file to Container
 * @param {*} phase Phase Message received from Log
 * @param {*} cur_ID Current Id of the Container
 */
function livelog_phase(phase, cur_ID) {
    "use strict";
    var id = "#log_phase_" + cur_ID;
    var $List = $(id);
    var $entry = $('<li>' + phase + '</li>');
    $List.append($entry);
}

/**
 * Bind the Module message from log file to container
 * @param {*} module Module Log message received from Log
 * @param {*} cur_ID Current Id of the container
 */
function livelog_module(module, cur_ID) {
    "use strict";
    var id = "#log_module_" + cur_ID;
    var $List = $(id);
    var $entry = $('<li>' + module + '</li>');
    $List.append($entry);
}

function getCookie(name) {
    "use strict";
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
  
/**
 * Removes the container from the UI
 * @param {*} currentID Id of the container which is passed backend to pull information
 */
function cancelLog(currentID) {
    "use strict";
    try {
        var idOfDIV = "#Container_" + currentID;
        $(idOfDIV).remove();
    } catch (error) {
        //console.log(error.message);
        console.log(error);
    }
}

/**
 * simple redirect to hashid associated with currentID
 * @param {*} currentID Id of the contaniner which is passed backend to pull information
 */
 function viewLog(currentID) {
    "use strict";
    try {
        // TODO get hashid of div-id
        window.location("/log/" + currentID);
    } catch (error) {
        //console.log(error.message);
        console.log(error);
    }
}

/**
 *  start socket connection just once TODO wss compatible? 
 */
var loc = window.location;
var wsStart = 'ws://';
var wsPort = ':8001';
if (loc.protocol == 'https:') {
      wsStart = 'wss://';
      wsPort = ':8000';
}
var socket = new WebSocket(
        wsStart + location.hostname + wsPort + '/ws/progress/'
);
/*for log implementation which is currently commented out*/
var module_array = [];
var phase_array = [];
var cur_len = 0;

/**
 * called when a websocket connection is established
 * */
socket.onopen = function () { 
    "use strict";
    console.log("[open] Connection established");
    socket.send("Reload");
};

/**
 * This method is called whenever a message from the backend arrives
 * */
socket.onmessage = function (event) {
    "use strict";
    console.log("Received a update");
    var data = JSON.parse(event.data);
    try{
        // for analysis in message create container
        for (var analysis_ in data){
            var htmlToAdd = `
            <div class="box" id="Container_` + Object.keys(data)[analysis_] + `">
                <div class="mainText">
                    <span>`+data[Object.keys(data)[analysis_]].firmware_name.split(".")[0]+`</span>
                </div>
                <div class="row">
                    <div class="col-sm log tile moduleLog">
                        <ul class="log_phase logUL" id="log_phase_` + Object.keys(data)[analysis_] + `"></ul>
                    </div>
                    <div class="col-sm log tile phaseLog">
                        <ul class="log_phase logUL" id="log_module_` + Object.keys(data)[analysis_] + `"></ul>
                    </div>
                </div>
                <div id="progress-wrapper">
                    <div id="pBar_` + Object.keys(data)[analysis_] + `" class="progress-bar" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                            0 % 
                    </div>
                </div>
            </div>
            <div class="buttonRow">
                <!--
                <button type="view-log" class="btn buttonRowElem" id="` + Object.keys(data)[analysis_] + `" onclick="viewLog(this.id)" >
                    EMBA-log
                </button>
                <button type="reset" class="btn buttonRowElem" id="` + Object.keys(data)[analysis_] + `" onclick="cancelLog(this.id)" >
                    Cancel
                </button>
                -->
            </div>`;
            document.getElementsByClassName("main")[0].insertAdjacentHTML('beforeend', htmlToAdd);
            // append phase and module arrays
            console.log("log_phase_" + Object.keys(data)[analysis_]);
            for (var module_ in data[analysis_].module_list){
                livelog_module(data[analysis_].module_list[module_], Object.keys(data)[analysis_])
            }
            for (var phase_ in data[analysis_].phase_list){
                livelog_module(data[analysis_].phase_list[phase_], Object.keys(data)[analysis_])
            }
            // set percentage and other metadata
            // TODO add metasinfo
            makeProgress(data[analysis_].percentage, Object.keys(data)[analysis_])
        }
    }
    catch(error){
        console.log(error);
    }
};

/**
 * This method is called when the websocket connection is closed
 *  */
socket.onclose = function () {
    "use strict";
    // console.error('Chat socket closed unexpectedly', event);
    console.log("[Socket]Closed Successfully");
};

/**
 * this method is called when an error occurs
 *  */
socket.onerror = function (err) {
    "use strict";
    //console.error('Socket encountered error: ', err.message, 'Closing socket');
    console.error('Socket encountered error: ', err);
    socket.close();
};

/* /**
 * Connection Established
 
function embaProgress() {
    console.log("Messaging started")
    setInterval(function () {
        socket.send("Hello");
    }, 3000);
}
 */

