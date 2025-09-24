const handleInput = (options) => {
    const inputValue =
        document
            .querySelector('.form-control').value;
//    const results =
//        ["apple", "banana", "cherry",
//            "date", "elderberry"];
    const parentElement =
        document
            .querySelector(".dropdown-menu");
    const elementsToRemove =
        document.querySelectorAll("li");

    elementsToRemove.forEach(element => {
        element.remove();
    });
    if (inputValue) {
        const matchingWords =
            options
                .filter(word => word
                    .includes(inputValue));
        matchingWords.sort((a, b) => {
            const indexA =
                a.indexOf(inputValue);
            const indexB =
                b.indexOf(inputValue);
            return indexA - indexB;
        });
        matchingWords.forEach(word => {
            const listItem =
                document.createElement("li");
            const link =
                document.createElement("a");
            link.classList.add("dropdown-item");
            link.href = "#";
            link.textContent = word;
            listItem.appendChild(link);
            parentElement.appendChild(listItem);
        });
        if (matchingWords.length == 0) {
            const listItem =
                document.createElement('li');
            listItem.textContent = "No Item";
            listItem.classList.add('dropdown-item');
            parentElement.appendChild(listItem);
        }
    } else {
        options.forEach(word => {
            const listItem =
                document.createElement("li");
            const link =
                document.createElement("a");
            link.classList.add("dropdown-item");
            link.href = "#";
            link.textContent = word;
            listItem.appendChild(link);
            parentElement.appendChild(listItem);
        });
    }
}
