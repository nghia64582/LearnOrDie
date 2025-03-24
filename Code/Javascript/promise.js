function task1() {
    const myPromise = new Promise((resolve, reject) => {
        // async operation
        setTimeout(() => {
            let success = false;
            if (success) {
                // resolve() is called when the operation is successful
                resolve("Data fetched successfully!");
            } else {
                // reject() is called when the operation fails
                reject("Error fetching data.");
            }
        }, 2000);
    });
}

function task2() {
    fetch('https://jsonplaceholder.typicode.com/posts/1')
        .then(response => response.json())
        .then(data => console.log(data))
        .catch(error => console.log(error));
    console.log('This is a message after the fetch call 1.');
    fetch('https://jsonplaceholder.typicode.com/posts/1')
        .then(response => response.json())
        .then(data => console.log(data))
        .catch(error => console.log(error));
        console.log('This is a message after the fetch call 2.');
}

task1();
// myPromise
//     .then(response => console.log(response))  // Executes when resolved
//     .catch(error => console.log(error));      // Executes when rejected