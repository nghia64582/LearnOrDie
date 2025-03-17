function showValue(value) {
    console.log(value);
}
let doLogin = () => {
    console.log('Login');
}
function doCancel() {
    console.log('Cancel');
}
function doAlert() {
    alert('Alert');
}
const showConfirm = () => {
    if (confirm("Are you sure?")) {
        alert('Yes');
    } else {
        alert('No');
    }
}