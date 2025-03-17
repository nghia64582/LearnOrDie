function Person(name, age) {
    this.name = name;
    this.age = age;
}

Person.prototype.job = "Software Engineer";

var a = Person("Alice", 25);
console.log(a.name);