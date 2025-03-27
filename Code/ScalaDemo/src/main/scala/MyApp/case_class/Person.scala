package MyApp.case_class

case class Person(name: String, age: Int) {

}

class Employee(var name: String, var age: Int) {

}

object MyPerson {

  def main(args: Array[String]): Unit = {
    val p: Person = Person.apply("Nghia", 25)
    val a = p.copy()
    val e = new Employee("Nghia", 24)
    e.name = "An"
    println(a)
    println(a == p)
    println(e.name + " : " + e.age)
  }
}
