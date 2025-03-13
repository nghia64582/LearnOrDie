function normalFunction() {
    console.log("This is a normal function")
}

const arrowFunction = () => {
    console.log("This is an arrow function")
}

(function immediatelyInvokedFunctionExpression() {
    console.log("This is an IIFE")
})()

const student = {
    name: "An",
    age: 25
};

(function introduce(student) {
    console.log(`Hello, my name is ${student.name}, I am ${student.age} years old`);
})(student);
normalFunction()
arrowFunction()