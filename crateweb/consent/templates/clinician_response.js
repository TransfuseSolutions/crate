{# clinician_response.js #}
{% comment %}
    template parameters:
        option_c_available: Python Boolean as "True" or something else
            ... converted here to Javascript Boolean as true or false
        initial_response
{% endcomment %}

var c_available_python = "{{ option_c_available }}";
var c_available = c_available_python == "True" ? true : false;
var initial_response = "{{ initial_response }}";

function startup() {
    // document.getElementById("debug").innerHTML += "initial_response: " + initial_response + ".";
    if (initial_response == 'A') {
        showA();
    } else if (initial_response == 'B') {
        showB();
    } else if (initial_response == 'C') {
        showC();
    } else if (initial_response == 'D') {
        showD();
    } else if (initial_response == 'R') {
        showR();
    } else {
        hideAll();
    }
}

function showStuff(a, b, c, d, r) {
    document.getElementById("optionA").style.display = a ? "block" : "none";
    document.getElementById("optionB").style.display = b ? "block" : "none";
    if (c_available) {
        document.getElementById("optionC").style.display = c ? "block" : "none";
    } else {
        document.getElementById("optionC").style.display = "none";
        document.getElementById("optionC_radio").style.display = "none";
    }
    document.getElementById("optionD").style.display = d ? "block" : "none";
    document.getElementById("optionR").style.display = r ? "block" : "none";
    document.getElementById("submit").style.display = (a || b || c || d || r) ? "block" : "none";
}

function hideAll() {
    showStuff(false, false, false, false, false);
}

function showA() {
    showStuff(true, false, false, false, false);
}

function showB() {
    showStuff(false, true, false, false, false);
}

function showC() {
    showStuff(false, false, true, false, false);
}

function showD() {
    showStuff(false, false, false, true, false);
}

function showR() {
    showStuff(false, false, false, false, true);
}
