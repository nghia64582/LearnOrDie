// setTimeout(() => {
//     console.log('Hello');
// }, 1000);

async function sayHello() {
    return new Promise(resolve => {
        setTimeout(() => {
            resolve("Returned after 1 second");
        }, 1000);
    });
}

sayHello().then(response => console.log(response));