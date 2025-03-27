package MyApp.companion_object

class Person (name: String, age: Int) {
  def greet(): Unit = {
    println(s"Hello, I'm $name, $age years old.")
  }
}

object Person {
  def apply(name: String, age: Int): Person = new Person(name, age)

  def create(name: String, age: Int): Person = {
    println("Create a new person")

    return new Person(name, age)
  }
}

object MyCompanion {
  def main(args: Array[String]): Unit = {
    val p: Person = Person.create("Nghia", 26)
    p.greet()
  }
}
