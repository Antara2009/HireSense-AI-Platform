COURSES = {
    "python": ("Python for Everybody", "https://www.freecodecamp.org/learn/scientific-computing-with-python/"),
    "sql": ("SQLBolt – Interactive SQL Lessons", "https://sqlbolt.com/"),
    "flask": ("Flask Documentation", "https://flask.palletsprojects.com/"),
    "machine learning": ("Google Machine Learning Crash Course", "https://developers.google.com/machine-learning/crash-course"),
    "pandas": ("Pandas Getting Started", "https://pandas.pydata.org/docs/getting_started/"),
    "numpy": ("NumPy Learn", "https://numpy.org/learn/"),
    "scikit-learn": ("Scikit-learn Tutorials", "https://scikit-learn.org/stable/tutorial/index.html"),
    "statistics": ("Khan Academy – Statistics", "https://www.khanacademy.org/math/statistics-probability"),
    "excel": ("Microsoft Excel Training", "https://support.microsoft.com/excel"),
    "power bi": ("Microsoft Learn – Power BI", "https://learn.microsoft.com/training/powerplatform/power-bi"),
    "html": ("MDN HTML Guide", "https://developer.mozilla.org/docs/Learn/HTML"),
    "css": ("MDN CSS Guide", "https://developer.mozilla.org/docs/Learn/CSS"),
    "javascript": ("JavaScript Guide – MDN", "https://developer.mozilla.org/docs/Web/JavaScript/Guide"),
    "react": ("React Learn", "https://react.dev/learn"),
    "java": (" dev.java – Learn Java", "https://dev.java/learn/"),
    "git": ("Git Handbook", "https://guides.github.com/introduction/git-handbook/"),
    "communication": ("Effective Communication – OpenLearn", "https://www.open.edu/openlearn/"),
    "problem solving": ("Problem Solving – OpenLearn", "https://www.open.edu/openlearn/"),
    "rest api": ("MDN – HTTP and APIs", "https://developer.mozilla.org/docs/Web/HTTP")
}

def recommend_courses(missing_skills):
    output = []
    for skill in missing_skills:
        key = skill.lower()
        title, link = COURSES.get(key, (f"Free learning resources for {skill.title()}", f"https://www.google.com/search?q=free+{skill.replace(' ', '+')}+course"))
        output.append({"skill": skill, "title": title, "url": link})
    return output
