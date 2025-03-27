package MyApp.`implicit_demo`

import scala.language.implicitConversions

case class Person(name: String, age: Int)

implicit def personToString(person: Person): String = {
  person.name
}

implicit def personToInt(person: Person): Int = {
  person.age
}

implicit def stringToInt(st: String): Int = {
  st.length
}

implicit class Student(person: Person) {
  def learn(): Unit = {
    println(s"${person.name} is learning")
  }
}

implicit class CityName(name: String) extends AnyVal {
  def introduceCity(): Unit = {
    println("This is city " + this.name)
  }
}

object MyImplicit {

  implicit val greeting: String = "Hello world"

  private def print(implicit greeting: String): Unit = {
    println(greeting)
  }

  def main(args: Array[String]): Unit = {
    // implicit conversion
    val person = Person("An", 24)
    val a: StringBuilder = new StringBuilder(person)
    a.append(" : z")
    println(a)
    val b: Int = person
    println(b * 2)


    // exp 2
    val st = "Nghia"
    println(st * 2)

    // implicit class
    person.learn()

    // implicit class
    val cityName = "Hanoi"
    cityName.introduceCity()

    print
  }

}
