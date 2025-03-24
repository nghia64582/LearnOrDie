// setTimeout(() => {
//     console.log('Hello');
// }, 1000);

async function sayHello() {
    let result = new Promise(resolve => {
        setTimeout(() => {
            resolve("Returned after 1 second");
        }, 1000);
    });
    return result;
}

sayHello().then(response => console.log(response));