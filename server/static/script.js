document.getElementById("slider").addEventListener("input", function() {
    var value = this.value;
    document.getElementById("value-display").innerHTML = value;
});
