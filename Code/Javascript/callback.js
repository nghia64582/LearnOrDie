function job1() {
    // callback hell
    function task1(callback) {
        console.log('Task 1');
        callback();
    }

    function task2(callback) {
        console.log('Task 2');
        callback();
    }

    function task3(callback) {
        console.log('Task 3');
        callback();
    }

    // callback hell
    task1(() => {
        task2(() => {
            task3(() => {
        
            });
        });
    });
}

function job2() {
    // using promises
    function task1() {
        console.log('Task 1');
        return Promise.resolve("Finish task 1");
    }
    function task2() {
        console.log('Task 2');
        return Promise.resolve("Finish task 2");
    }
    function task3() {
        console.log('Task 3');
        return Promise.resolve("Finish task 3");
    }
    task1()
        .then(response => {
            console.log(response);
            task2()
            .then(response => {
                console.log(response);
                task3();
            });
        });
}
job2();